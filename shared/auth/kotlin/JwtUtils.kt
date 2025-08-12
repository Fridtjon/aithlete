package com.aithlete.shared.auth

import io.jsonwebtoken.*
import io.jsonwebtoken.security.Keys
import org.springframework.beans.factory.annotation.Value
import org.springframework.security.core.Authentication
import org.springframework.security.core.userdetails.UserDetails
import org.springframework.stereotype.Component
import java.time.Instant
import java.time.temporal.ChronoUnit
import java.util.*
import javax.crypto.SecretKey

/**
 * Shared JWT utilities for all Kotlin services
 */
@Component
class JwtUtils(
    @Value("\${app.jwt.secret}") private val jwtSecret: String,
    @Value("\${app.jwt.expiration:86400}") private val jwtExpirationInSeconds: Long
) {
    
    private val key: SecretKey by lazy {
        Keys.hmacShaKeyFor(jwtSecret.toByteArray())
    }

    /**
     * Generate JWT token from Authentication
     */
    fun generateToken(authentication: Authentication): String {
        val userPrincipal = authentication.principal as UserDetails
        return generateToken(userPrincipal.username)
    }

    /**
     * Generate JWT token from username and optional userId
     */
    fun generateToken(username: String, userId: String? = null): String {
        val expiryDate = Date.from(Instant.now().plus(jwtExpirationInSeconds, ChronoUnit.SECONDS))

        val claims = Jwts.claims().setSubject(username)
        userId?.let { claims["userId"] = it }

        return Jwts.builder()
            .setClaims(claims)
            .setIssuedAt(Date())
            .setExpiration(expiryDate)
            .signWith(key)
            .compact()
    }

    /**
     * Extract username from token
     */
    fun getUsernameFromToken(token: String): String {
        return getClaimsFromToken(token).subject
    }

    /**
     * Extract user ID from token
     */
    fun getUserIdFromToken(token: String): String? {
        return getClaimsFromToken(token)["userId"] as? String
    }

    /**
     * Extract expiration date from token
     */
    fun getExpirationDateFromToken(token: String): Date {
        return getClaimsFromToken(token).expiration
    }

    /**
     * Check if token is expired
     */
    fun isTokenExpired(token: String): Boolean {
        val expiration = getExpirationDateFromToken(token)
        return expiration.before(Date())
    }

    /**
     * Validate JWT token
     */
    fun validateToken(authToken: String): Boolean {
        try {
            Jwts.parserBuilder()
                .setSigningKey(key)
                .build()
                .parseClaimsJws(authToken)
            return true
        } catch (ex: SecurityException) {
            logger.error("Invalid JWT signature", ex)
        } catch (ex: MalformedJwtException) {
            logger.error("Invalid JWT token", ex)
        } catch (ex: ExpiredJwtException) {
            logger.error("Expired JWT token", ex)
        } catch (ex: UnsupportedJwtException) {
            logger.error("Unsupported JWT token", ex)
        } catch (ex: IllegalArgumentException) {
            logger.error("JWT claims string is empty", ex)
        }
        return false
    }

    /**
     * Extract all claims from token
     */
    private fun getClaimsFromToken(token: String): Claims {
        return Jwts.parserBuilder()
            .setSigningKey(key)
            .build()
            .parseClaimsJws(token)
            .body
    }

    companion object {
        private val logger = org.slf4j.LoggerFactory.getLogger(JwtUtils::class.java)
        
        /**
         * Extract JWT token from Authorization header
         */
        fun extractTokenFromHeader(authHeader: String?): String? {
            return if (authHeader != null && authHeader.startsWith("Bearer ")) {
                authHeader.substring(7)
            } else null
        }
    }
}