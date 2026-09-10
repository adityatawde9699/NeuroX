package org.neurox.patient

import android.Manifest
import android.os.Build
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.work.CoroutineWorker
import androidx.work.Data
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.HttpException
import java.io.IOException
import java.time.Duration
import java.time.Instant
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.time.ZoneId
import java.util.concurrent.TimeUnit

object ReminderScheduler {
    private const val WORK_PREFIX = "neurox-reminder-"

    fun scheduleAll(context: Context, reminders: List<ReminderItem>) {
        reminders.forEach { reminder ->
            if (reminder.enabled && reminder.status !in setOf("done", "missed")) {
                schedule(context, reminder)
            } else {
                WorkManager.getInstance(context).cancelUniqueWork(WORK_PREFIX + reminder.id)
            }
        }
    }

    fun schedule(context: Context, reminder: ReminderItem, delayOverrideMinutes: Long? = null) {
        val delay = delayOverrideMinutes?.let { Duration.ofMinutes(it) }
            ?: Duration.between(Instant.now(), nextOccurrence(reminder)).coerceAtLeast(Duration.ZERO)
        val input = Data.Builder()
            .putString("id", reminder.id)
            .putString("title", reminder.title)
            .putString("type", reminder.type)
            .putString("repeat", reminder.repeatRule)
            .putString("scheduled", reminder.scheduledTime)
            .putString("timezone", reminder.timezoneName)
            .build()
        val request = OneTimeWorkRequestBuilder<ReminderNotificationWorker>()
            .setInitialDelay(delay.toMillis(), TimeUnit.MILLISECONDS)
            .setInputData(input)
            .build()
        WorkManager.getInstance(context).enqueueUniqueWork(
            WORK_PREFIX + reminder.id,
            ExistingWorkPolicy.REPLACE,
            request,
        )
    }

    fun rescheduleFromCache(context: Context) {
        val request = OneTimeWorkRequestBuilder<ReminderRescheduleWorker>().build()
        WorkManager.getInstance(context).enqueueUniqueWork(
            "neurox-reminder-reschedule", ExistingWorkPolicy.REPLACE, request,
        )
    }

    private fun nextOccurrence(reminder: ReminderItem): Instant {
        val requested = reminder.snoozedUntil ?: reminder.scheduledTime
        var instant = runCatching { OffsetDateTime.parse(requested).toInstant() }.getOrElse {
            LocalDateTime.parse(requested).atZone(ZoneId.of(reminder.timezoneName)).toInstant()
        }
        val step = when (reminder.repeatRule?.lowercase()) {
            "daily" -> Duration.ofDays(1)
            "weekly" -> Duration.ofDays(7)
            else -> null
        }
        while (step != null && instant.isBefore(Instant.now())) instant = instant.plus(step)
        return instant
    }
}

class ReminderNotificationWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        val id = inputData.getString("id") ?: return Result.failure()
        // The work request can outlive a server-side edit or deletion. Re-check
        // the current offline source of truth before showing anything.
        val cached = OfflineDatabase.get(applicationContext).offlineCacheDao().reminder(id)
            ?: return Result.success()
        if (!cached.enabled || cached.status in setOf("done", "missed")) return Result.success()
        val title = cached.title
        val type = cached.type
        createChannel(applicationContext, type)
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(applicationContext, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            return Result.success()
        }
        val done = actionIntent(applicationContext, id, "done", 1)
        val snooze = actionIntent(applicationContext, id, "snoozed", 2)
        val detail = if (type == "medication")
            "Please check your care plan. Marking done does not confirm medicine was taken."
        else "Open NeuroX when you are ready."
        val notification = NotificationCompat.Builder(applicationContext, "neurox-$type")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(title)
            .setContentText(detail)
            .setStyle(NotificationCompat.BigTextStyle().bigText(detail))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .addAction(0, "Snooze 10 min", snooze)
            .addAction(0, "Done", done)
            .build()
        NotificationManagerCompat.from(applicationContext).notify(id.hashCode(), notification)
        scheduleMissedCheck(applicationContext, id)
        cached.repeatRule?.let {
            ReminderScheduler.schedule(
                applicationContext,
                ReminderItem(id, title, cached.scheduledTime, false, cached.description,
                    type, cached.repeatRule, cached.enabled, cached.status, cached.snoozedUntil, cached.timezoneName),
            )
        }
        return Result.success()
    }

    private fun createChannel(context: Context, type: String) {
        val manager = context.getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(NotificationChannel(
            "neurox-$type", "${type.replaceFirstChar { it.uppercase() }} reminders",
            NotificationManager.IMPORTANCE_HIGH,
        ).apply { description = "Supportive NeuroX reminders without dosage or treatment advice." })
    }

    private fun actionIntent(context: Context, id: String, action: String, code: Int): PendingIntent {
        val intent = Intent(context, ReminderActionReceiver::class.java)
            .putExtra("id", id).putExtra("action", action)
        return PendingIntent.getBroadcast(
            context, id.hashCode() + code, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }

    private fun scheduleMissedCheck(context: Context, id: String) {
        val request = OneTimeWorkRequestBuilder<ReminderActionWorker>()
            .setInitialDelay(1, TimeUnit.HOURS)
            .setInputData(Data.Builder().putString("id", id).putString("action", "missed").build())
            .build()
        WorkManager.getInstance(context).enqueueUniqueWork(
            "neurox-reminder-missed-$id", ExistingWorkPolicy.REPLACE, request,
        )
    }
}

class ReminderActionReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val id = intent.getStringExtra("id") ?: return
        val action = intent.getStringExtra("action") ?: return
        val request = OneTimeWorkRequestBuilder<ReminderActionWorker>()
            .setInputData(Data.Builder().putString("id", id).putString("action", action).build())
            .build()
        WorkManager.getInstance(context).enqueue(request)
        NotificationManagerCompat.from(context).cancel(id.hashCode())
    }
}

class ReminderActionWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val id = inputData.getString("id") ?: return@withContext Result.failure()
        val action = inputData.getString("action") ?: return@withContext Result.failure()
        val repository = PatientDependencies.repository(applicationContext)
        val cached = OfflineDatabase.get(applicationContext).offlineCacheDao().reminder(id)
            ?: return@withContext Result.success()
        if (action == "missed" && cached.status != "upcoming") return@withContext Result.success()
        val snoozedUntil = if (action == "snoozed") Instant.now().plusSeconds(600).toString() else null
        try {
            repository.updateReminderState(id, action, snoozedUntil)
        } catch (_: IOException) {
            repository.queueReminderState(id, action, snoozedUntil)
        } catch (_: HttpException) {
            return@withContext Result.failure()
        }
        repository.updateReminderStateLocally(id, action, snoozedUntil)
        if (action == "snoozed") {
            ReminderScheduler.schedule(
                applicationContext,
                ReminderItem(id, cached.title, cached.scheduledTime, false, cached.description,
                    cached.type, cached.repeatRule, cached.enabled, action, snoozedUntil, cached.timezoneName),
                delayOverrideMinutes = 10,
            )
        }
        Result.success()
    }
}

class ReminderRescheduleWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val reminders = OfflineDatabase.get(applicationContext).offlineCacheDao().reminders().map {
            ReminderItem(it.id, it.title, it.scheduledTime, it.completed, it.description,
                it.type, it.repeatRule, it.enabled, it.status, it.snoozedUntil, it.timezoneName)
        }
        ReminderScheduler.scheduleAll(applicationContext, reminders)
        Result.success()
    }
}
