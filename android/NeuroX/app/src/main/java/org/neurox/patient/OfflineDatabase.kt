package org.neurox.patient

import android.content.Context
import android.database.sqlite.SQLiteException
import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Room
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import java.io.File

@Entity(tableName = "pending_sync_events")
data class PendingSyncEntity(
    @androidx.room.PrimaryKey val eventId: String,
    val eventType: String,
    val patientId: String,
    val payloadJson: String,
    val createdAt: Long,
    val status: String = "pending",
    val retryCount: Int = 0,
    val lastError: String? = null
)

@Entity(tableName = "cached_patient")
data class CachedPatientEntity(
    @androidx.room.PrimaryKey val id: String,
    val name: String,
    val age: Int,
    val preferredLanguage: String,
    val fetchedAt: Long
)

@Entity(tableName = "cached_activities")
data class CachedActivityEntity(
    @androidx.room.PrimaryKey val id: String,
    val title: String,
    val description: String,
    val difficulty: Int,
    val contentVersion: String,
    val fetchedAt: Long
)

@Entity(tableName = "cached_reminders")
data class CachedReminderEntity(
    @androidx.room.PrimaryKey val id: String,
    val title: String,
    val scheduledTime: String,
    val completed: Boolean,
    val description: String?,
    val type: String,
    val repeatRule: String?,
    val enabled: Boolean,
    val status: String,
    val snoozedUntil: String?,
    val timezoneName: String,
    val fetchedAt: Long
)

@Entity(tableName = "cached_snapshots")
data class CachedSnapshotEntity(
    @androidx.room.PrimaryKey val category: String,
    val payloadJson: String,
    val fetchedAt: Long
)

@Dao
interface PendingSyncDao {
    @Query("SELECT COUNT(*) FROM pending_sync_events")
    suspend fun countAll(): Int
    @Query("SELECT * FROM pending_sync_events WHERE status = 'pending' ORDER BY createdAt ASC")
    suspend fun getAll(): List<PendingSyncEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(event: PendingSyncEntity)

    @Query("DELETE FROM pending_sync_events WHERE eventId IN (:eventIds)")
    suspend fun delete(eventIds: List<String>)

    @Query("UPDATE pending_sync_events SET status = 'failed', lastError = :error, retryCount = retryCount + 1 WHERE eventId IN (:eventIds)")
    suspend fun markFailed(eventIds: List<String>, error: String)
}

@Dao
interface OfflineCacheDao {
    @Query("SELECT * FROM cached_patient LIMIT 1")
    suspend fun patient(): CachedPatientEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun savePatient(patient: CachedPatientEntity)

    @Query("SELECT * FROM cached_activities ORDER BY id ASC")
    suspend fun activities(): List<CachedActivityEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveActivities(activities: List<CachedActivityEntity>)

    @Query("DELETE FROM cached_activities")
    suspend fun clearActivities()

    @Query("SELECT * FROM cached_reminders ORDER BY scheduledTime ASC")
    suspend fun reminders(): List<CachedReminderEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveReminders(reminders: List<CachedReminderEntity>)

    @Query("DELETE FROM cached_reminders")
    suspend fun clearReminders()

    @Query("UPDATE cached_reminders SET completed = 1 WHERE id = :reminderId")
    suspend fun markReminderCompleted(reminderId: String)

    @Query("UPDATE cached_reminders SET completed = :completed, status = :status, snoozedUntil = :snoozedUntil WHERE id = :reminderId")
    suspend fun updateReminderState(reminderId: String, completed: Boolean, status: String, snoozedUntil: String?)

    @Query("SELECT * FROM cached_reminders WHERE id = :reminderId LIMIT 1")
    suspend fun reminder(reminderId: String): CachedReminderEntity?

    @Query("SELECT * FROM cached_snapshots WHERE category = :category LIMIT 1")
    suspend fun snapshot(category: String): CachedSnapshotEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveSnapshot(snapshot: CachedSnapshotEntity)
}

@Database(entities = [PendingSyncEntity::class, CachedPatientEntity::class, CachedActivityEntity::class, CachedReminderEntity::class, CachedSnapshotEntity::class], version = 6, exportSchema = false)
abstract class OfflineDatabase : androidx.room.RoomDatabase() {
    abstract fun pendingSyncDao(): PendingSyncDao
    abstract fun offlineCacheDao(): OfflineCacheDao

    /** Keep a checkpointed last-known-good copy for bounded corruption recovery. */
    fun checkpointBackup() {
        openHelper.writableDatabase.query("PRAGMA wal_checkpoint(FULL)").close()
        val source = File(
            checkNotNull(openHelper.writableDatabase.path) { "Offline database path is unavailable." }
        )
        val backup = File("${source.path}.backup")
        val temporary = File("${backup.path}.tmp")
        source.copyTo(temporary, overwrite = true)
        check(temporary.renameTo(backup)) { "Could not finalize offline database backup." }
    }

    companion object {
        @Volatile private var instance: OfflineDatabase? = null

        fun get(context: Context): OfflineDatabase = instance ?: synchronized(this) {
            instance ?: openWithRecovery(context.applicationContext).also { instance = it }
        }

        private fun build(context: Context) = Room.databaseBuilder(
                context.applicationContext,
                OfflineDatabase::class.java,
                "neurox-offline.db"
            ).addMigrations(MIGRATION_1_2, MIGRATION_2_3, MIGRATION_3_4, MIGRATION_4_5, MIGRATION_5_6).build()

        private fun openWithRecovery(context: Context): OfflineDatabase {
            val candidate = build(context)
            try {
                candidate.openHelper.writableDatabase
                return candidate
            } catch (error: SQLiteException) {
                candidate.close()
                val database = context.getDatabasePath("neurox-offline.db")
                val backup = File("${database.path}.backup")
                if (!backup.isFile) throw error
                File("${database.path}-wal").delete()
                File("${database.path}-shm").delete()
                backup.copyTo(database, overwrite = true)
                val recovered = build(context)
                recovered.openHelper.writableDatabase
                return recovered
            }
        }

        internal fun closeForTest() = synchronized(this) {
            instance?.close()
            instance = null
        }

        private val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(database: SupportSQLiteDatabase) {
                database.execSQL("ALTER TABLE pending_sync_events ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'")
                database.execSQL("ALTER TABLE pending_sync_events ADD COLUMN retryCount INTEGER NOT NULL DEFAULT 0")
                database.execSQL("ALTER TABLE pending_sync_events ADD COLUMN lastError TEXT")
            }
        }

        private val MIGRATION_2_3 = object : Migration(2, 3) {
            override fun migrate(database: SupportSQLiteDatabase) {
                database.execSQL("CREATE TABLE IF NOT EXISTS cached_patient (id TEXT NOT NULL PRIMARY KEY, name TEXT NOT NULL, age INTEGER NOT NULL, preferredLanguage TEXT NOT NULL, fetchedAt INTEGER NOT NULL)")
                database.execSQL("CREATE TABLE IF NOT EXISTS cached_activities (id TEXT NOT NULL PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL, difficulty INTEGER NOT NULL, fetchedAt INTEGER NOT NULL)")
                database.execSQL("CREATE TABLE IF NOT EXISTS cached_reminders (id TEXT NOT NULL PRIMARY KEY, title TEXT NOT NULL, scheduledTime TEXT NOT NULL, completed INTEGER NOT NULL, description TEXT, fetchedAt INTEGER NOT NULL)")
            }
        }

        private val MIGRATION_3_4 = object : Migration(3, 4) {
            override fun migrate(database: SupportSQLiteDatabase) {
                database.execSQL("CREATE TABLE IF NOT EXISTS cached_snapshots (category TEXT NOT NULL PRIMARY KEY, payloadJson TEXT NOT NULL, fetchedAt INTEGER NOT NULL)")
            }
        }

        private val MIGRATION_4_5 = object : Migration(4, 5) {
            override fun migrate(database: SupportSQLiteDatabase) {
                database.execSQL("ALTER TABLE cached_activities ADD COLUMN contentVersion TEXT NOT NULL DEFAULT 'legacy'")
            }
        }

        private val MIGRATION_5_6 = object : Migration(5, 6) {
            override fun migrate(database: SupportSQLiteDatabase) {
                database.execSQL("ALTER TABLE cached_reminders ADD COLUMN type TEXT NOT NULL DEFAULT 'activity'")
                database.execSQL("ALTER TABLE cached_reminders ADD COLUMN repeatRule TEXT")
                database.execSQL("ALTER TABLE cached_reminders ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1")
                database.execSQL("ALTER TABLE cached_reminders ADD COLUMN status TEXT NOT NULL DEFAULT 'upcoming'")
                database.execSQL("ALTER TABLE cached_reminders ADD COLUMN snoozedUntil TEXT")
                database.execSQL("ALTER TABLE cached_reminders ADD COLUMN timezoneName TEXT NOT NULL DEFAULT 'Asia/Kolkata'")
            }
        }
    }
}
