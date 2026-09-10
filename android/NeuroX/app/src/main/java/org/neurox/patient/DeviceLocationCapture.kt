package org.neurox.patient

import android.annotation.SuppressLint
import android.content.Context
import android.location.Location
import android.location.LocationManager
import android.os.Build
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import java.time.Instant
import kotlin.coroutines.resume

data class DeviceLocation(
    val latitude: Double,
    val longitude: Double,
    val accuracyM: Double,
    val capturedAt: String,
)

/** Captures one consent-gated fix while the patient app is in the foreground. */
class DeviceLocationCapture(private val context: Context) {
    @SuppressLint("MissingPermission")
    suspend fun current(): DeviceLocation? = withContext(Dispatchers.Main.immediate) {
        val manager = context.getSystemService(LocationManager::class.java) ?: return@withContext null
        val provider = when {
            manager.isProviderEnabled(LocationManager.GPS_PROVIDER) -> LocationManager.GPS_PROVIDER
            manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER) -> LocationManager.NETWORK_PROVIDER
            else -> return@withContext null
        }
        val location = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            suspendCancellableCoroutine<Location?> { continuation ->
                manager.getCurrentLocation(provider, null, context.mainExecutor) { fix ->
                    if (continuation.isActive) continuation.resume(fix)
                }
                continuation.invokeOnCancellation { /* platform request is short-lived */ }
            }
        } else {
            manager.getLastKnownLocation(provider)
        } ?: return@withContext null
        DeviceLocation(
            latitude = location.latitude,
            longitude = location.longitude,
            accuracyM = location.accuracy.toDouble().coerceAtLeast(1.0),
            capturedAt = Instant.ofEpochMilli(location.time).toString(),
        )
    }
}
