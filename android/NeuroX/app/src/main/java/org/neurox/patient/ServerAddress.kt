package org.neurox.patient

import java.net.URI

fun validatedServerAddress(value: String, allowHttp: Boolean): String {
    val uri = try { URI(value.trim()) } catch (_: Exception) {
        throw IllegalArgumentException("Enter a valid server address.")
    }
    require(uri.scheme == "https" || (allowHttp && uri.scheme == "http")) {
        "Use an HTTPS server address."
    }
    require(!uri.host.isNullOrBlank() && uri.userInfo == null && uri.query == null && uri.fragment == null) {
        "Enter a server address without credentials, a query, or a fragment."
    }
    require(uri.port == -1 || uri.port in 1..65535) { "Enter a valid server port." }
    return uri.toASCIIString().trimEnd('/') + "/"
}
