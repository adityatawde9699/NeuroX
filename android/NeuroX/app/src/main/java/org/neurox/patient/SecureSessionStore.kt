package org.neurox.patient

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import com.google.gson.Gson
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

data class PatientSession(
    val server: String,
    val patientId: String,
    val accessToken: String? = null,
    val refreshToken: String? = null
)

/** Tokens are encrypted with a non-exportable Android Keystore key. */
class SecureSessionStore(context: Context) {
    private val preferences = context.getSharedPreferences("neurox_secure_session", Context.MODE_PRIVATE)
    private val gson = Gson()

    init {
        // Force a fresh sign-in for prototype installs; retain the device binding
        // so queued events cannot be uploaded to another account or server.
        val legacy = context.getSharedPreferences("neurox_session", Context.MODE_PRIVATE)
        val owner = legacy.getString("patient_id", null)
        if (owner != null && read() == null && BuildConfig.DEFAULT_API_URL.isNotEmpty()) {
            save(PatientSession(BuildConfig.DEFAULT_API_URL, owner))
        }
        check(legacy.edit().clear().commit()) { "Unable to remove the old session." }
    }

    fun read(): PatientSession? = synchronized(lock) {
        val payload = preferences.getString("session", null) ?: return@synchronized null
        try {
            val parts = payload.split(":")
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, Base64.decode(parts[0], Base64.NO_WRAP)))
            gson.fromJson(String(cipher.doFinal(Base64.decode(parts[1], Base64.NO_WRAP)), Charsets.UTF_8), PatientSession::class.java)
        } catch (_: Exception) {
            // A missing/invalidated key must never fall back to plaintext tokens.
            null
        }
    }

    fun save(session: PatientSession) = synchronized(lock) {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val encrypted = cipher.doFinal(gson.toJson(session).toByteArray(Charsets.UTF_8))
        val payload = Base64.encodeToString(cipher.iv, Base64.NO_WRAP) + ":" +
            Base64.encodeToString(encrypted, Base64.NO_WRAP)
        check(preferences.edit().putString("session", payload).commit()) { "Unable to save the session securely." }
        changes.value += 1
    }

    fun expire() = synchronized(lock) {
        read()?.let { save(it.copy(accessToken = null, refreshToken = null)) }
    }

    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
            init(KeyGenParameterSpec.Builder(KEY_ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build())
        }.generateKey()
    }

    companion object {
        val lock = Any()
        val changes = kotlinx.coroutines.flow.MutableStateFlow(0L)
        private const val KEY_ALIAS = "neurox.session.v1"
    }
}
