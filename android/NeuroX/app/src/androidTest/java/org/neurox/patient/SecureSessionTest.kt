package org.neurox.patient

import android.content.Context
import android.content.ContextWrapper
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.util.UUID

@RunWith(AndroidJUnit4::class)
class SecureSessionTest {
    private fun isolatedContext(): Context {
        val prefix = "test-${UUID.randomUUID()}-"
        return object : ContextWrapper(ApplicationProvider.getApplicationContext<Context>()) {
            override fun getSharedPreferences(name: String, mode: Int) = super.getSharedPreferences(prefix + name, mode)
        }
    }

    @Test fun encryptsTokensAndPreservesBindingOnExpiry() {
        val context = isolatedContext()
        val store = SecureSessionStore(context)
        val original = PatientSession("https://care.example/", "patient-1", "access-secret", "refresh-secret")
        store.save(original)
        val payload = context.getSharedPreferences("neurox_secure_session", Context.MODE_PRIVATE).getString("session", "")!!
        assertFalse(payload.contains("access-secret"))
        assertFalse(payload.contains("refresh-secret"))
        assertEquals(original, SecureSessionStore(context).read())
        store.expire()
        assertEquals(original.copy(accessToken = null, refreshToken = null), store.read())
    }

    @Test fun corruptCiphertextDoesNotRestoreASession() {
        val context = isolatedContext()
        val store = SecureSessionStore(context)
        context.getSharedPreferences("neurox_secure_session", Context.MODE_PRIVATE)
            .edit().putString("session", "corrupt:ciphertext").commit()
        assertNull(store.read())
    }

    @Test fun expiredAccessTokenRotatesAndRetries() = runBlocking {
        val server = MockWebServer()
        server.start()
        try {
            val address = server.url("/").toString()
            val store = SecureSessionStore(isolatedContext())
            store.save(PatientSession(address, "patient-1", "expired", "refresh-old"))
            server.enqueue(MockResponse().setResponseCode(401))
            server.enqueue(MockResponse().setBody("""{"access_token":"fresh","refresh_token":"refresh-new","user":{"id":"patient-1","role":"PATIENT","name":"Patient","email":"p@example.com"}}"""))
            server.enqueue(MockResponse().setBody("""{"id":"patient-1","name":"Patient","age":70,"preferredLanguage":"English"}"""))
            assertEquals("patient-1", patientApi(address, store).patient().id)
            assertEquals("Bearer expired", server.takeRequest().getHeader("Authorization"))
            val refresh = server.takeRequest()
            assertEquals("/api/v1/auth/refresh", refresh.path)
            assertNull(refresh.getHeader("Authorization"))
            assertEquals("Bearer fresh", server.takeRequest().getHeader("Authorization"))
            assertEquals("refresh-new", store.read()?.refreshToken)
        } finally { server.shutdown() }
    }
}
