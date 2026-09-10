package org.neurox.patient

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class OfflineDatabaseMigrationTest {
    private val context = ApplicationProvider.getApplicationContext<Context>()

    @Before fun createVersionOneDatabase() {
        OfflineDatabase.closeForTest()
        context.deleteDatabase("neurox-offline.db")
        context.openOrCreateDatabase("neurox-offline.db", Context.MODE_PRIVATE, null).use { db ->
            db.execSQL("CREATE TABLE pending_sync_events (eventId TEXT NOT NULL PRIMARY KEY, eventType TEXT NOT NULL, patientId TEXT NOT NULL, payloadJson TEXT NOT NULL, createdAt INTEGER NOT NULL)")
            db.execSQL("INSERT INTO pending_sync_events VALUES ('event-1', 'sos_event', 'patient-1', '{}', 1)")
            db.version = 1
        }
    }

    @After fun cleanUp() {
        OfflineDatabase.closeForTest()
        context.deleteDatabase("neurox-offline.db")
        context.getDatabasePath("neurox-offline.db.backup").delete()
    }

    @Test fun migratesVersionOneToCurrentWithoutLosingPendingEvent() = runBlocking {
        val migrated = OfflineDatabase.get(context)
        val queued = migrated.pendingSyncDao().getAll()
        assertEquals(1, queued.size)
        assertEquals("event-1", queued.single().eventId)
        assertEquals("pending", queued.single().status)
        assertEquals(0, queued.single().retryCount)
    }

    @Test fun restoresLastCheckpointAfterDatabaseCorruption() = runBlocking {
        val migrated = OfflineDatabase.get(context)
        migrated.checkpointBackup()
        OfflineDatabase.closeForTest()
        context.getDatabasePath("neurox-offline.db").writeBytes(byteArrayOf(1, 2, 3, 4))

        val recovered = OfflineDatabase.get(context)
        assertEquals("event-1", recovered.pendingSyncDao().getAll().single().eventId)
    }
}
