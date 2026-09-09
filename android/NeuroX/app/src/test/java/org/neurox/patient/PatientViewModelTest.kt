package org.neurox.patient

import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import java.io.IOException

@OptIn(ExperimentalCoroutinesApi::class)
class PatientViewModelTest {
    @Before fun setUp() { Dispatchers.setMain(StandardTestDispatcher()) }
    @After fun tearDown() { Dispatchers.resetMain() }

    @Test fun offlineRefreshUsesCachedPatientAndPendingCount() = runTest {
        val repository = FakePatientRepository().apply { offline = true; pending = 3 }
        val model = PatientViewModel(repository)
        advanceUntilIdle()
        assertEquals("Test Patient", model.state.value.patientName)
        assertEquals(SyncState.Offline, model.state.value.syncState)
        assertEquals(3, model.state.value.pendingCount)
        assertNull(model.state.value.lastSyncedLabel)
    }

    @Test fun corruptCacheShowsErrorWithoutUncaughtCoroutineFailure() = runTest {
        val model = PatientViewModel(FakePatientRepository().apply { offline = true; cacheFailure = true })
        advanceUntilIdle()
        assertEquals(SyncState.Error, model.state.value.syncState)
    }

    @Test fun offlineCompletionKeepsStartEventIdAndIsQueuedOnlyOnce() = runTest {
        val repository = FakePatientRepository().apply { offline = true }
        val model = PatientViewModel(repository)
        advanceUntilIdle()
        model.start(defaultActivities.first())
        advanceUntilIdle()
        model.finish("memory-match", .8f, 5f, 2)
        model.finish("memory-match", .8f, 5f, 2)
        advanceUntilIdle()
        assertEquals(1, repository.completions.size)
        assertEquals(repository.startedEventId, repository.completions.single().eventId)
        assertTrue(repository.completions.single().offlineCreated)
        assertNull(model.state.value.activeActivity)
        assertEquals(1, model.state.value.pendingCount)
    }

    @Test fun repeatedStartAndNavigationDoNotOpenALateActivity() = runTest {
        val repository = FakePatientRepository().apply { startGate = CompletableDeferred() }
        val model = PatientViewModel(repository)
        advanceUntilIdle()
        model.start(defaultActivities.first())
        model.start(defaultActivities.first())
        runCurrent()
        assertEquals(1, repository.startCalls)
        model.leaveActivity()
        repository.startGate!!.complete(Unit)
        advanceUntilIdle()
        assertNull(model.state.value.activeActivity)
    }

    @Test fun offlineReminderIsQueuedBeforeShowingCompletion() = runTest {
        val repository = FakePatientRepository().apply { offline = true }
        val model = PatientViewModel(repository)
        advanceUntilIdle()
        model.completeReminder("reminder-1")
        advanceUntilIdle()
        assertTrue(model.state.value.reminders.single().completed)
        assertEquals(1, model.state.value.pendingCount)
        assertEquals(listOf("queue", "local"), repository.reminderSteps)
    }

    @Test fun failedReminderQueueDoesNotClaimCompletion() = runTest {
        val model = PatientViewModel(FakePatientRepository().apply { offline = true; queueFailure = true })
        advanceUntilIdle()
        model.completeReminder("reminder-1")
        advanceUntilIdle()
        assertFalse(model.state.value.reminders.single().completed)
        assertEquals(SyncState.Error, model.state.value.syncState)
    }

    @Test fun failedSosQueueShowsError() = runTest {
        val model = PatientViewModel(FakePatientRepository().apply { offline = true; queueFailure = true })
        advanceUntilIdle()
        model.sendHelp()
        advanceUntilIdle()
        assertEquals(SyncState.Error, model.state.value.syncState)
        assertEquals(0, model.state.value.pendingCount)
    }

    @Test fun serverRejectionDoesNotQueueAnUnauthorizedAction() = runTest {
        val repository = FakePatientRepository().apply { reject = true }
        val model = PatientViewModel(repository)
        advanceUntilIdle()
        model.sendHelp()
        advanceUntilIdle()
        assertEquals(SyncState.Error, model.state.value.syncState)
        assertEquals(0, repository.pending)
    }

    @Test fun onlineCompletionAppliesBoundedDifficulty() = runTest {
        val model = PatientViewModel(FakePatientRepository())
        advanceUntilIdle()
        model.start(defaultActivities.first())
        advanceUntilIdle()
        model.finish("memory-match", .9f, 8f, 1)
        advanceUntilIdle()
        assertEquals(5, model.state.value.activities.first().difficulty)
        assertEquals(SyncState.Synced, model.state.value.syncState)
    }
}

private class FakePatientRepository : PatientRepository {
    var offline = false
    var reject = false
    var cacheFailure = false
    var queueFailure = false
    var pending = 0
    var startCalls = 0
    var startedEventId: String? = null
    var startGate: CompletableDeferred<Unit>? = null
    val completions = mutableListOf<ActivityCompletionRequest>()
    val reminderSteps = mutableListOf<String>()
    private val reminder = ReminderItem("reminder-1", "Water", "09:00", false)
    private val data = RemoteData(Patient("patient-1", "Test Patient", 70, "English"), defaultActivities, listOf(reminder))

    private fun network() {
        if (reject) error("Server rejected the action")
        if (offline) throw IOException("Offline")
    }
    private fun queue() { check(!queueFailure) { "Disk unavailable" }; pending++ }
    override suspend fun load(): RemoteData { network(); return data }
    override suspend fun cachedData(): RemoteData { check(!cacheFailure); return data }
    override suspend fun pendingEventCount() = pending
    override fun schedulePendingSync() {}
    override fun patientId() = "patient-1"
    override suspend fun startActivity(activity: ActivityItem, eventId: String, startedAt: String, offline: Boolean): Map<String, Any> {
        startCalls++
        startedEventId = eventId
        startGate?.await()
        network()
        return emptyMap()
    }
    override suspend fun completeActivity(activity: ActivityItem, request: ActivityCompletionRequest): SyncResult {
        network()
        return SyncResult(nextDifficulty = 9)
    }
    override suspend fun queueActivityCompletion(request: ActivityCompletionRequest) { queue(); completions.add(request) }
    override suspend fun markReminderComplete(reminderId: String): ReminderItem { network(); return reminder.copy(completed = true) }
    override suspend fun markReminderCompletedLocally(reminderId: String) { reminderSteps.add("local") }
    override suspend fun queueReminderUpdate(reminderId: String) { queue(); reminderSteps.add("queue") }
    override suspend fun sendSos(request: SosRequest): Map<String, Any> { network(); return emptyMap() }
    override suspend fun queueSos(request: SosRequest, eventId: String) { queue() }
}
