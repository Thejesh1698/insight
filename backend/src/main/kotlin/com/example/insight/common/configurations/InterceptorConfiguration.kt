package com.example.insight.common.configurations

import org.springframework.beans.factory.annotation.Autowired
import org.springframework.stereotype.Component
import org.springframework.web.servlet.config.annotation.InterceptorRegistry
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer

@Component
class InterceptorConfiguration: WebMvcConfigurer {

    @Autowired
    private lateinit var eventTrackingInterceptor: com.example.insight.common.configurations.interceptors.EventTrackingInterceptor

    override fun addInterceptors(registry: InterceptorRegistry) {

        registry.addInterceptor(eventTrackingInterceptor)
    }
}