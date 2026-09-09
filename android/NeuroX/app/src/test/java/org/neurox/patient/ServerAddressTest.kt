package org.neurox.patient

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class ServerAddressTest {
    @Test fun releaseRequiresHttpsAndRejectsCredentialBearingAddresses() {
        listOf("http://example.com", "https://user:pass@example.com", "https://example.com?q=token",
            "https://example.com#secret", "file:///tmp/server", "https://", "https://example.com:99999").forEach {
            assertThrows(it, IllegalArgumentException::class.java) { validatedServerAddress(it, false) }
        }
    }
    @Test fun normalizesServerPathsAndAllowsDebugHttp() {
        assertEquals("https://example.com/api/", validatedServerAddress(" https://example.com/api ", false))
        assertEquals("http://10.0.2.2:8000/", validatedServerAddress("http://10.0.2.2:8000", true))
    }
}
