package com.aithlete.gateway.controller

import mu.KotlinLogging
import org.springframework.beans.factory.annotation.Value
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*
import org.springframework.web.reactive.function.client.WebClient
import java.net.URI

@RestController
@RequestMapping("/api/v1")
class GatewayController(
    private val webClient: WebClient,
    @Value("\${services.user-service.url}") private val userServiceUrl: String,
    @Value("\${services.data-aggregation-service.url}") private val dataAggregationServiceUrl: String,
    @Value("\${services.garmin-service.url}") private val garminServiceUrl: String,
    @Value("\${services.hevy-service.url}") private val hevyServiceUrl: String,
    @Value("\${services.ai-planning-service.url}") private val aiPlanningServiceUrl: String,
    @Value("\${services.email-service.url}") private val emailServiceUrl: String
) {

    private val logger = KotlinLogging.logger {}

    // User service proxy endpoints
    @GetMapping("/users/{userId}")
    fun getUser(@PathVariable userId: String, @RequestHeader headers: Map<String, String>): ResponseEntity<Any> {
        return proxyRequest("GET", "$userServiceUrl/users/$userId", null, headers)
    }

    @PostMapping("/users")
    fun createUser(@RequestBody body: Any, @RequestHeader headers: Map<String, String>): ResponseEntity<Any> {
        return proxyRequest("POST", "$userServiceUrl/users", body, headers)
    }

    @GetMapping("/users/{userId}/goals")
    fun getUserGoals(@PathVariable userId: String, @RequestHeader headers: Map<String, String>): ResponseEntity<Any> {
        return proxyRequest("GET", "$userServiceUrl/users/$userId/goals", null, headers)
    }

    // Data aggregation service proxy endpoints
    @GetMapping("/data/activities")
    fun getActivities(@RequestParam userId: String, @RequestParam(defaultValue = "30") days: Int, @RequestHeader headers: Map<String, String>): ResponseEntity<Any> {
        return proxyRequest("GET", "$dataAggregationServiceUrl/data/activities?userId=$userId&days=$days", null, headers)
    }

    @GetMapping("/data/metrics")
    fun getMetrics(@RequestParam userId: String, @RequestParam metricType: String, @RequestParam(defaultValue = "7") days: Int, @RequestHeader headers: Map<String, String>): ResponseEntity<Any> {
        return proxyRequest("GET", "$dataAggregationServiceUrl/data/metrics?userId=$userId&metricType=$metricType&days=$days", null, headers)
    }

    // AI Planning service proxy endpoints
    @PostMapping("/planning/generate")
    fun generatePlan(@RequestBody body: Any, @RequestHeader headers: Map<String, String>): ResponseEntity<Any> {
        return proxyRequest("POST", "$aiPlanningServiceUrl/planning/generate", body, headers)
    }

    @GetMapping("/plans/{userId}")
    fun getUserPlan(@PathVariable userId: String, @RequestParam(defaultValue = "latest") version: String, @RequestHeader headers: Map<String, String>): ResponseEntity<Any> {
        return proxyRequest("GET", "$aiPlanningServiceUrl/plans/$userId?version=$version", null, headers)
    }

    // Data sync endpoints
    @PostMapping("/sync/garmin")
    fun syncGarminData(@RequestParam userId: String, @RequestHeader headers: Map<String, String>): ResponseEntity<Any> {
        return proxyRequest("POST", "$garminServiceUrl/sync?userId=$userId", null, headers)
    }

    @PostMapping("/sync/hevy")
    fun syncHevyData(@RequestParam userId: String, @RequestHeader headers: Map<String, String>): ResponseEntity<Any> {
        return proxyRequest("POST", "$hevyServiceUrl/sync?userId=$userId", null, headers)
    }

    // Email service endpoints
    @PostMapping("/email/digest")
    fun sendDigest(@RequestBody body: Any, @RequestHeader headers: Map<String, String>): ResponseEntity<Any> {
        return proxyRequest("POST", "$emailServiceUrl/email/digest", body, headers)
    }

    private fun proxyRequest(method: String, url: String, body: Any?, headers: Map<String, String>): ResponseEntity<Any> {
        return try {
            logger.info("Proxying $method request to $url")
            
            val response = when (method.uppercase()) {
                "GET" -> webClient.get()
                    .uri(URI(url))
                    .headers { httpHeaders ->
                        headers.forEach { (key, value) -> 
                            if (!key.lowercase().startsWith("host")) {
                                httpHeaders.add(key, value)
                            }
                        }
                    }
                    .retrieve()
                    .toEntity(Any::class.java)
                    .block()

                "POST" -> webClient.post()
                    .uri(URI(url))
                    .headers { httpHeaders ->
                        headers.forEach { (key, value) -> 
                            if (!key.lowercase().startsWith("host")) {
                                httpHeaders.add(key, value)
                            }
                        }
                    }
                    .bodyValue(body ?: "")
                    .retrieve()
                    .toEntity(Any::class.java)
                    .block()

                else -> throw UnsupportedOperationException("HTTP method $method not supported")
            }

            response ?: ResponseEntity.internalServerError().build()
        } catch (ex: Exception) {
            logger.error("Error proxying request to $url", ex)
            ResponseEntity.internalServerError()
                .body(mapOf("error" to "Service unavailable", "message" to ex.message))
        }
    }
}