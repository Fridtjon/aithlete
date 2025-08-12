package com.aithlete.gateway.security

import jakarta.servlet.FilterChain
import jakarta.servlet.http.HttpServletRequest
import jakarta.servlet.http.HttpServletResponse
import mu.KotlinLogging
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken
import org.springframework.security.core.context.SecurityContextHolder
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource
import org.springframework.util.StringUtils
import org.springframework.web.filter.OncePerRequestFilter

class JwtAuthenticationFilter(
    private val tokenProvider: JwtTokenProvider
) : OncePerRequestFilter() {

    private val logger = KotlinLogging.logger {}

    override fun doFilterInternal(
        request: HttpServletRequest,
        response: HttpServletResponse,
        filterChain: FilterChain
    ) {
        try {
            val jwt = getJwtFromRequest(request)
            
            if (StringUtils.hasText(jwt) && tokenProvider.validateToken(jwt!!)) {
                val username = tokenProvider.getUsernameFromToken(jwt)
                val userId = tokenProvider.getUserIdFromToken(jwt)
                
                // Create authentication token
                val authentication = UsernamePasswordAuthenticationToken(
                    username,
                    null,
                    emptyList() // Authorities can be added later
                ).apply {
                    details = WebAuthenticationDetailsSource().buildDetails(request)
                }
                
                // Set user ID in request attributes for controllers
                userId?.let { request.setAttribute("userId", it) }
                
                SecurityContextHolder.getContext().authentication = authentication
            }
        } catch (ex: Exception) {
            logger.error("Could not set user authentication in security context", ex)
        }

        filterChain.doFilter(request, response)
    }

    private fun getJwtFromRequest(request: HttpServletRequest): String? {
        val bearerToken = request.getHeader("Authorization")
        return if (StringUtils.hasText(bearerToken) && bearerToken.startsWith("Bearer ")) {
            bearerToken.substring(7)
        } else null
    }
}