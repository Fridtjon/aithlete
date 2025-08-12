package com.aithlete.gateway.controller

import org.springframework.beans.factory.annotation.Value
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController
import java.time.Instant

@RestController
@RequestMapping("/api/v1/health")
class HealthController(
    @Value("\${spring.application.name:api-gateway}") private val serviceName: String
) {

    @GetMapping
    fun health(): ResponseEntity<Map<String, Any>> {
        return ResponseEntity.ok(
            mapOf(
                "service" to serviceName,
                "status" to "healthy",
                "timestamp" to Instant.now().toString(),
                "version" to javaClass.`package`.implementationVersion ?: "development"
            )
        )
    }

    @GetMapping("/ready")
    fun readiness(): ResponseEntity<Map<String, Any>> {
        // Add actual readiness checks here (database connectivity, external services, etc.)
        return ResponseEntity.ok(
            mapOf(
                "service" to serviceName,
                "ready" to true,
                "timestamp" to Instant.now().toString()
            )
        )
    }

    @GetMapping("/live")
    fun liveness(): ResponseEntity<Map<String, Any>> {
        // Add actual liveness checks here
        return ResponseEntity.ok(
            mapOf(
                "service" to serviceName,
                "alive" to true,
                "timestamp" to Instant.now().toString()
            )
        )
    }
}