package org.neurox.patient

/** Authenticated Retrofit adapter; constructing it does not require sign-in. */
class PatientRemoteDataSource(private val sessions: SecureSessionStore) {
    val api: NeuroXApi by lazy {
        patientApi(sessions.read()?.server ?: error("Please sign in first."), sessions)
    }

    suspend fun load(): RemoteData {
        val patient = api.patient()
        val activities = api.activities()
        val reminders = api.reminders(patient.id)
        val history = api.activityHistory(patient.id)
        val contacts = api.emergencyContacts(patient.id)
        val safety = api.safety(patient.id)
        return RemoteData(patient, activities, reminders, history, contacts, safety)
    }
}
