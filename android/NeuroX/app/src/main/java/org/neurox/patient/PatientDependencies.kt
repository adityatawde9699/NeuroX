package org.neurox.patient

import android.content.Context

/** Manual dependency injection shared by UI and background workers. */
object PatientDependencies {
    fun repository(context: Context): NeuroXRepository {
        val app = context.applicationContext
        val sessions = SecureSessionStore(app)
        return NeuroXRepository(sessions, PatientLocalDataSource(OfflineDatabase.get(app)),
            PatientRemoteDataSource(sessions), { SyncWorker.enqueue(app) })
    }
}
