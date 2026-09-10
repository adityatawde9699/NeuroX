package org.neurox.patient

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/** Re-check queued work when reboot or wall-clock configuration may affect scheduling. */
class SyncRescheduleReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action in supportedActions) {
            SyncWorker.enqueue(context.applicationContext)
            ReminderScheduler.rescheduleFromCache(context.applicationContext)
        }
    }

    private companion object {
        val supportedActions = setOf(
            Intent.ACTION_BOOT_COMPLETED,
            Intent.ACTION_LOCKED_BOOT_COMPLETED,
            Intent.ACTION_TIME_CHANGED,
            Intent.ACTION_TIMEZONE_CHANGED,
        )
    }
}
