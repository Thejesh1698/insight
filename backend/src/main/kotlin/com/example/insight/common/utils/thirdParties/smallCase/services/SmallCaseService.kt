package com.example.insight.common.utils.thirdParties.smallCase.services


import com.example.insight.common.models.entities.User
import com.example.insight.common.utils.thirdParties.smallCase.models.responses.TransactionCreationResponse
import com.example.insight.common.utils.thirdParties.smallCase.properties.SmallCaseProperties
import com.example.insight.common.utils.thirdParties.smallCase.utils.SmallCaseApiUtils
import io.jsonwebtoken.Jwts
import io.jsonwebtoken.SignatureAlgorithm
import org.apache.commons.codec.digest.HmacAlgorithms
import org.apache.commons.codec.digest.HmacUtils
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.stereotype.Service
import java.util.*
import javax.crypto.spec.SecretKeySpec

@Service
class SmallCaseService(val smallCaseProperties: SmallCaseProperties) {

    @Autowired
    lateinit var smallCaseApiUtils: SmallCaseApiUtils

    fun createTransaction(
        user: User,
        userSmallCaseAuthToken: String,
        isGuestSession: Boolean,
        notes: String?
    ): Triple<String, TransactionCreationResponse.TransactionCreationData, String> {

        val token = getSignedJwtToken(smallCaseProperties.secret, userSmallCaseAuthToken, isGuestSession)

        val requestPayload = hashMapOf<String, Any?>(
            "intent" to "HOLDINGS_IMPORT",
            "version" to "v2",
            "assetConfig" to hashMapOf(
                "mfHoldings" to false
            ),
            "notes" to notes //max-limit: 256 characters
        )
        val (response, responseString) = smallCaseApiUtils.creatTransaction(user.userId, token, requestPayload)
        return Triple(token, response, responseString)
    }

    private fun getSignedJwtToken(key: String, userSmallCaseAuthToken: String, isGuestSession: Boolean): String {

        val signatureAlgorithm: SignatureAlgorithm = SignatureAlgorithm.HS256
        val signingKey = SecretKeySpec(key.toByteArray(), signatureAlgorithm.jcaName)

        val cal = Calendar.getInstance()
        val issuedAt = Date()
        cal.setTime(issuedAt)
        cal.add(Calendar.DATE, 1)
        val expireAt: Date = cal.time

        return if(isGuestSession) {
            Jwts.builder()
                .claim(userSmallCaseAuthToken, true)
                .setExpiration(expireAt)
                .setIssuedAt(issuedAt)
                .signWith(signatureAlgorithm, signingKey)
                .compact()
        } else {
            Jwts.builder()
                .claim("smallcaseAuthId", userSmallCaseAuthToken)
                .setExpiration(expireAt)
                .setIssuedAt(issuedAt)
                .signWith(signatureAlgorithm, signingKey)
                .compact()
        }

    }

    fun generateChecksum(timestamp: String, smallcaseAuthId: String): String {
        return HmacUtils(
            HmacAlgorithms.HMAC_SHA_256,
            smallCaseProperties.apiGatewaySecret.toByteArray()
        ).hmacHex("$timestamp$smallcaseAuthId")
    }
}