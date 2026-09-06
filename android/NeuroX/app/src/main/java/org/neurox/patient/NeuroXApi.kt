package org.neurox.patient

import android.content.Context
import com.google.gson.annotations.SerializedName
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path

data class LoginRequest(val email: String, val password: String)
data class AuthResponse(@SerializedName("access_token") val accessToken: String, @SerializedName("refresh_token") val refreshToken: String, val user: User)
data class User(val id: String, val name: String, val email: String, val role: String)
data class Patient(val id: String, val name: String, val age: Int, val preferredLanguage: String)
data class ActivityItem(val id: String, val title: String, val description: String, val difficulty: Int)
data class ReminderItem(val id: String, val title: String, val scheduledTime: String, val completed: Boolean, val description: String? = null)
data class ActivityStartRequest(@SerializedName("user_id") val userId: String, @SerializedName("difficulty_level") val difficultyLevel: Int, @SerializedName("started_at") val startedAt: String, @SerializedName("event_id") val eventId: String, @SerializedName("offline_created") val offlineCreated: Boolean = false)
data class ActivityCompletionRequest(@SerializedName("user_id") val userId: String, @SerializedName("activity_id") val activityId: String, @SerializedName("started_at") val startedAt: String, @SerializedName("completed_at") val completedAt: String, val accuracy: Float, @SerializedName("response_time") val responseTime: Float, val attempts: Int, @SerializedName("completion_status") val completionStatus: String = "completed", @SerializedName("difficulty_level") val difficultyLevel: Int, @SerializedName("offline_created") val offlineCreated: Boolean = false, @SerializedName("event_id") val eventId: String)
data class SyncResult(val saved: Boolean = true, val message: String? = null, @SerializedName("next_difficulty") val nextDifficulty: Int? = null, @SerializedName("performance_score") val performanceScore: Float? = null)

interface NeuroXApi {
    @POST("auth/login") suspend fun login(@Body request: LoginRequest): AuthResponse
    @GET("patients/me") suspend fun patient(): Patient
    @GET("activities") suspend fun activities(): List<ActivityItem>
    @GET("patients/{patientId}/reminders") suspend fun reminders(@Path("patientId") patientId: String): List<ReminderItem>
    @PUT("reminders/{reminderId}") suspend fun completeReminder(@Path("reminderId") reminderId: String, @Body request: Map<String, Boolean>): ReminderItem
    @POST("activities/{activityId}/start") suspend fun startActivity(@Path("activityId") activityId: String, @Body request: ActivityStartRequest): Map<String, Any>
    @POST("activities/{activityId}/complete") suspend fun completeActivity(@Path("activityId") activityId: String, @Body request: ActivityCompletionRequest): SyncResult
}

class NeuroXRepository(context: Context) {
    private val preferences = context.getSharedPreferences("neurox_session", Context.MODE_PRIVATE)
    private val gson = com.google.gson.Gson()
    private val api = Retrofit.Builder().baseUrl("http://10.0.2.2:8000/").addConverterFactory(GsonConverterFactory.create()).client(okhttp3.OkHttpClient.Builder().addInterceptor { chain ->
        val token = preferences.getString("access_token", null)
        chain.proceed(chain.request().newBuilder().apply { if (token != null) addHeader("Authorization", "Bearer $token") }.build())
    }.build()).build().create(NeuroXApi::class.java)

    suspend fun load(): RemoteData = withContext(Dispatchers.IO) {
        if (preferences.getString("access_token", null) == null) {
            val auth = api.login(LoginRequest("maya@neurox.demo", "NeuroXDemo!2026"))
            preferences.edit().putString("access_token", auth.accessToken).putString("patient_id", auth.user.id).apply()
        }
        val patient = api.patient()
        return@withContext RemoteData(patient, api.activities(), api.reminders(patient.id)).also { cached ->
            preferences.edit().putString("cached_data", gson.toJson(cached)).apply()
        }
    }

    fun cachedData(): RemoteData? = preferences.getString("cached_data", null)?.let {
        runCatching { gson.fromJson(it, RemoteData::class.java) }.getOrNull()
    }

    suspend fun markReminderComplete(reminderId: String) = api.completeReminder(reminderId, mapOf("completed" to true))
    suspend fun startActivity(activity: ActivityItem, eventId: String, startedAt: String, offline: Boolean) = api.startActivity(activity.id, ActivityStartRequest(userId = patientId(), difficultyLevel = activity.difficulty, startedAt = startedAt, eventId = eventId, offlineCreated = offline))
    suspend fun completeActivity(activity: ActivityItem, request: ActivityCompletionRequest) = api.completeActivity(activity.id, request)
    fun patientId(): String = preferences.getString("patient_id", "maya-demo") ?: "maya-demo"
}

data class RemoteData(val patient: Patient, val activities: List<ActivityItem>, val reminders: List<ReminderItem>)