package com.example.insight.common.filters

import com.fasterxml.jackson.databind.ObjectMapper
import com.example.insight.common.errorHandler.ApiError
import com.example.insight.common.errorHandler.exceptions.CustomException
import com.example.insight.common.errorHandler.exceptions.ForbiddenRequestException
import com.example.insight.common.errorHandler.exceptions.InternalServerErrorException
import com.example.insight.features.userAuthentication.services.UserAuthenticationService
import jakarta.servlet.Filter
import jakarta.servlet.FilterChain
import jakarta.servlet.ServletRequest
import jakarta.servlet.ServletResponse
import jakarta.servlet.http.HttpServletRequest
import jakarta.servlet.http.HttpServletResponse

class AuthenticationFilter(private val userAuthenticationService: UserAuthenticationService) :
    Filter {

    private val objectMapper = ObjectMapper()

    /**
     * If authentication is successful, proceed to the next filter or servlet in the chain
     * If authentication fails, you can handle it accordingly (e.g., return an unauthorized response)
     */
    override fun doFilter(request: ServletRequest, response: ServletResponse, chain: FilterChain) {

        try {
            val httpRequest: HttpServletRequest = request as HttpServletRequest
            val requestURI = httpRequest.requestURI

            // Check the request URI pattern and perform authentication accordingly
            when {
                requestURI.startsWith("/public/") -> authenticatePublicApiRequest()
                requestURI.startsWith("/client/") -> authenticateClientApiRequest(httpRequest, request)
                requestURI.startsWith("/cloud/") -> authenticateCloudApiRequest()
                else -> {
                    println("Unrecognised api request --- requestURI: ${httpRequest.requestURI}")
                    throw ForbiddenRequestException()
                }
            }

            chain.doFilter(request, response)
        } catch (exception: CustomException) {
            print(exception)
            val apiError = ApiError(exception)
            writeApiResponse(response, apiError, HttpServletResponse.SC_UNAUTHORIZED)
        } catch (exception: Exception) {
            print(exception)
            val internalServerException = InternalServerErrorException()
            val apiError = ApiError(internalServerException)
            writeApiResponse(response, apiError, HttpServletResponse.SC_INTERNAL_SERVER_ERROR)
        }
    }

    private fun authenticateClientApiRequest(httpRequest: HttpServletRequest, request: ServletRequest) {

        val authToken: String = httpRequest.getHeader("X-AUTH-TOKEN") ?: run {
            println(
                "request received for an client api without auth token --- request: ${
                    objectMapper.writeValueAsString(
                        request
                    )
                } | authToken: ${null} | userId: ${httpRequest.getHeader("X-USER-ID")}"
            )
            throw ForbiddenRequestException()
        }
        val userId: Long = httpRequest.getHeader("X-USER-ID")?.toLong() ?: run {
            println("request received for an client api without userId --- requestURI: ${httpRequest.requestURI} | authToken: $authToken | userId: ${null}")
            throw ForbiddenRequestException()
        }

        validateUserIdInHeaderAndPathMatch(userId, httpRequest)

        val user = userAuthenticationService.authenticateUser(authToken, userId)

        request.setAttribute("user", user)
    }

    private fun authenticatePublicApiRequest() {

        //do nothing and maybe log in future if required
    }

    private fun authenticateCloudApiRequest() {

        // add a basic authentication for api calls that are being called within your cloud VPC/network
    }

    private fun writeApiResponse(response: ServletResponse, apiError: ApiError, statusCode: Int) {
        response.contentType = "application/json"
        (response as HttpServletResponse).status = statusCode
        val writer = response.writer
        writer.write(objectMapper.writeValueAsString(apiError))
        writer.flush()
    }

    private fun validateUserIdInHeaderAndPathMatch(userIdFromHeader: Long, httpRequest: HttpServletRequest) {

        val pathInfo = httpRequest.requestURI
        val userIdPattern = Regex("/users/(\\d+)")
        val matchResult = userIdPattern.find(pathInfo)
        val userIdFromPath = matchResult?.groupValues?.get(1)?.toLongOrNull()

        if (userIdFromPath != null && userIdFromHeader != userIdFromPath) {
            println("User ID in the header ($userIdFromHeader) doesn't match the User ID in the path ($userIdFromPath).")
            throw ForbiddenRequestException()
        }
    }
}

