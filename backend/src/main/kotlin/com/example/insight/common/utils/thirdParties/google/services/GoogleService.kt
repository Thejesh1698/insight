package com.example.insight.common.utils.thirdParties.google.services

import com.google.api.client.googleapis.auth.oauth2.GoogleIdTokenVerifier
import com.google.api.client.http.javanet.NetHttpTransport
import com.google.api.client.json.JsonFactory
import com.google.api.client.json.gson.GsonFactory
import com.example.insight.common.errorHandler.exceptions.InternalServerErrorException
import com.example.insight.common.utils.thirdParties.google.models.responses.GoogleOauthValidationResponse
import com.example.insight.common.utils.thirdParties.google.properties.GoogleProperties
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Service


@Service
class GoogleService(val googleProperties: GoogleProperties) {

    val logger: Logger = LoggerFactory.getLogger(this.javaClass)

    fun validateTokenAndFetchUserDetails(accessToken: String, userEmail: String?): GoogleOauthValidationResponse {

        try {
            val transport = NetHttpTransport()
            val jsonFactory: JsonFactory = GsonFactory()

            val verifier = GoogleIdTokenVerifier.Builder(transport, jsonFactory)
                .setAudience(listOf(googleProperties.oauth.clientId))
                .build()

            val googleIdToken = verifier.verify(accessToken)
            val googleProvidedEmail = googleIdToken.payload.email
            val userName = googleIdToken.payload["name"]?.toString()
            val userId = googleIdToken.payload.subject

            return GoogleOauthValidationResponse(
                googleProvidedEmail,
                userName,
                userId
            )
        } catch (exception: Exception) {
            logger.error("Error while validating google Oauth access token --- accessToken: $accessToken | " +
                    "userEmail: $userEmail")
            exception.printStackTrace()
            throw InternalServerErrorException()
        }
    }
}