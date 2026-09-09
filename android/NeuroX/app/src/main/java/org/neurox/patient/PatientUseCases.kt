package org.neurox.patient

import java.io.IOException

sealed interface Delivery<out T> {
    data class Online<T>(val value: T) : Delivery<T>
    data object Queued : Delivery<Nothing>
}

/** Only transport failures are queued; rejected requests and cancellation propagate. */
class CompleteActivity(private val repository: PatientRepository) {
    suspend operator fun invoke(activity: ActivityItem, request: ActivityCompletionRequest): Delivery<SyncResult> =
        try {
            Delivery.Online(repository.completeActivity(activity, request))
        } catch (_: IOException) {
            repository.queueActivityCompletion(request.copy(offlineCreated = true))
            Delivery.Queued
        }
}

class CompleteReminder(private val repository: PatientRepository) {
    suspend operator fun invoke(id: String): Delivery<RemoteData> = try {
        repository.markReminderComplete(id)
        Delivery.Online(repository.load())
    } catch (_: IOException) {
        // Persist before presenting a locally completed reminder.
        repository.queueReminderUpdate(id)
        repository.markReminderCompletedLocally(id)
        Delivery.Queued
    }
}

class SendHelp(private val repository: PatientRepository) {
    suspend operator fun invoke(request: SosRequest): Delivery<Unit> = try {
        repository.sendSos(request)
        Delivery.Online(Unit)
    } catch (_: IOException) {
        repository.queueSos(request)
        Delivery.Queued
    }
}
