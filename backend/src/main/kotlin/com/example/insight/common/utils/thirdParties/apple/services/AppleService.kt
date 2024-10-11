package com.example.insight.common.utils.thirdParties.apple.services

import com.example.insight.common.errorHandler.exceptions.InternalServerErrorException
import com.example.insight.common.utils.thirdParties.apple.models.responses.AppleOauthValidationResponse
import com.example.insight.common.utils.thirdParties.apple.properties.AppleProperties
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Service
import org.jose4j.jwk.HttpsJwks
import org.jose4j.jwt.consumer.JwtConsumerBuilder
import org.jose4j.keys.resolvers.HttpsJwksVerificationKeyResolver

@Service
class AppleService(val appleProperties: AppleProperties) {

    val logger: Logger = LoggerFactory.getLogger(this.javaClass)

    fun validateTokenAndFetchUserDetails(accessToken: String, userEmail: String?): AppleOauthValidationResponse {

        val httpsJkws = HttpsJwks(appleProperties.oauth.publicAuthKeysApi)

        val httpsJkwsKeyResolver = HttpsJwksVerificationKeyResolver(httpsJkws)

        val jwtConsumer = JwtConsumerBuilder()
            .setVerificationKeyResolver(httpsJkwsKeyResolver)
            .setExpectedIssuer("https://appleid.apple.com")
            .setExpectedAudience(appleProperties.oauth.clientId)
            .build()

        val jwtClaims = jwtConsumer.processToClaims(accessToken)

        val emailFromApple = jwtClaims.claimsMap["email"]?.toString()
        val nameFromApple = jwtClaims.claimsMap["name"]?.toString()

        if(emailFromApple.isNullOrBlank()) {
            logger.error("user email or user name cannot be null from apple --- accessToke: $accessToken | " +
                    "userEmail: $userEmail | emailFromApple: $emailFromApple | nameFromApple: $nameFromApple")
            throw InternalServerErrorException()
        }

        return AppleOauthValidationResponse(
            emailFromApple,
            nameFromApple
        )
    }
}