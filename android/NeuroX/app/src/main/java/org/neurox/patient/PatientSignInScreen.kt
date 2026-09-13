package org.neurox.patient

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.Image
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun PatientSignInScreen(state: PatientAuthState, onSignIn: (String, String, String) -> Unit) {
    var server by rememberSaveable(state.server) { mutableStateOf(state.server) }
    var email by rememberSaveable { mutableStateOf("") }
    // Passwords are deliberately excluded from saved-instance state.
    var password by remember { mutableStateOf("") }
    Column(Modifier.fillMaxSize().imePadding().verticalScroll(rememberScrollState()).padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(20.dp)) {
        Image(
            painter = painterResource(R.drawable.neurox_logo),
            contentDescription = "NeuroX",
            modifier = Modifier.size(190.dp),
            contentScale = ContentScale.Fit,
        )
        Text("Welcome to NeuroX", fontSize = 30.sp)
        Text("Ask your caregiver to help you sign in with your patient account.", fontSize = 20.sp)
        OutlinedTextField(server, { server = it }, label = { Text("Server address") },
            modifier = Modifier.fillMaxWidth(), singleLine = true, enabled = !state.busy,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri))
        OutlinedTextField(email, { email = it }, label = { Text("Patient email") },
            modifier = Modifier.fillMaxWidth(), singleLine = true, enabled = !state.busy,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email))
        OutlinedTextField(password, { password = it }, label = { Text("Password") },
            modifier = Modifier.fillMaxWidth(), singleLine = true, enabled = !state.busy,
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password))
        state.error?.let { Text(it, color = MaterialTheme.colorScheme.error, fontSize = 18.sp) }
        Button(onClick = {
            onSignIn(server, email, password)
            password = ""
        }, enabled = !state.busy && server.isNotBlank() && email.isNotBlank() && password.length >= 8,
            modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp)) {
            Text(if (state.busy) "Signing in…" else "Sign in", fontSize = 22.sp)
        }
        Text("You need a connection for first sign-in. Saved activities remain available offline after setup.")
    }
}
