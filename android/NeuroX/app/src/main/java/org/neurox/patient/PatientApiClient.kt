package org.neurox.patient

import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

fun patientApi(server: String, sessions: SecureSessionStore? = null): NeuroXApi {
    val client = OkHttpClient.Builder().followRedirects(false).followSslRedirects(false)
    if (sessions != null) {
        client.addInterceptor { chain ->
            val session = sessions.read()
            val request = chain.request().newBuilder()
            if (session?.server == server && session.accessToken != null) {
                request.header("Authorization", "Bearer ${session.accessToken}")
            }
            chain.proceed(request.build())
        }
        client.authenticator { _, response ->
            synchronized(SecureSessionStore.lock) {
                val session = sessions.read() ?: return@synchronized null
                if (session.server != server || response.priorResponse != null) return@synchronized null
                val previous = response.request.header("Authorization")
                if (session.accessToken != null && previous != "Bearer ${session.accessToken}") {
                    return@synchronized response.request.newBuilder()
                        .header("Authorization", "Bearer ${session.accessToken}").build()
                }
                val refreshToken = session.refreshToken ?: run {
                    sessions.expire()
                    return@synchronized null
                }
                // A separate client prevents recursive authentication on refresh.
                val refreshed = patientApi(server).refresh(RefreshTokenRequest(refreshToken)).execute()
                if (!refreshed.isSuccessful) {
                    if (refreshed.code() == 401 || refreshed.code() == 403) sessions.expire()
                    if (refreshed.code() >= 500 || refreshed.code() == 429) {
                        throw java.io.IOException("Session service is temporarily unavailable.")
                    }
                    return@synchronized null
                }
                val auth = refreshed.body() ?: return@synchronized null
                if (auth.user.id != session.patientId || auth.user.role != "PATIENT") {
                    sessions.expire()
                    return@synchronized null
                }
                sessions.save(session.copy(accessToken = auth.accessToken, refreshToken = auth.refreshToken))
                response.request.newBuilder().header("Authorization", "Bearer ${auth.accessToken}").build()
            }
        }
    }
    return Retrofit.Builder().baseUrl(server).client(client.build())
        .addConverterFactory(GsonConverterFactory.create()).build().create(NeuroXApi::class.java)
}
