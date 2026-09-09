package org.neurox.patient

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import retrofit2.HttpException
import java.io.IOException

data class PatientAuthState(
    val checking: Boolean = true,
    val signedIn: Boolean = false,
    val server: String = "",
    val busy: Boolean = false,
    val error: String? = null
)

class PatientAuthViewModel(application: Application) : AndroidViewModel(application) {
    val repository = PatientDependencies.repository(application)
    private val mutableState = MutableStateFlow(PatientAuthState())
    val state = mutableState.asStateFlow()

    init {
        viewModelScope.launch {
            SecureSessionStore.changes.collect {
                val signedIn = withContext(Dispatchers.IO) { repository.hasSession() }
                val server = withContext(Dispatchers.IO) { repository.configuredServer() }
                mutableState.update { it.copy(checking = false, signedIn = signedIn, server = server) }
            }
        }
    }

    fun signIn(server: String, email: String, password: String) {
        if (state.value.busy) return
        mutableState.update { it.copy(busy = true, error = null) }
        viewModelScope.launch {
            try {
                repository.signIn(server, email, password)
                mutableState.update { it.copy(signedIn = true) }
            } catch (error: CancellationException) {
                throw error
            } catch (error: Exception) {
                val message = when (error) {
                    is HttpException -> when (error.code()) {
                        401 -> "Email or password was not recognized. Please try again."
                        403, 404 -> "A patient profile is needed. Ask your caregiver to complete setup."
                        else -> "The server could not complete sign-in. Please try again."
                    }
                    is IOException -> "Cannot connect. Check your internet connection and server address."
                    is IllegalArgumentException -> error.message ?: "Check your sign-in details."
                    else -> "Unable to sign in securely. Please try again."
                }
                mutableState.update { it.copy(error = message) }
            } finally {
                mutableState.update { it.copy(busy = false) }
            }
        }
    }
}
