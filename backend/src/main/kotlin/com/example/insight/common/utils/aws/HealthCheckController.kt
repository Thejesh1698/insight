package com.example.insight.common.utils.aws

import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RestController

@RestController
class HealthCheckController {

    /**
     * Public api for AWS Elastic Beanstalk to check for server's running status
     */
    @GetMapping("/public/server/health-check", produces = ["application/json"])
    fun getHealthCheckOfServer(): ResponseEntity<String> {

        return ResponseEntity(
            "Server is online", HttpStatus.OK
        )
    }
}