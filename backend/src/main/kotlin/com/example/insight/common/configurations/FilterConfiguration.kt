package com.example.insight.common.configurations

import com.example.insight.common.filters.AuthenticationFilter
import com.example.insight.features.userAuthentication.services.UserAuthenticationService
import jakarta.servlet.Filter
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.web.servlet.FilterRegistrationBean
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration

@Configuration
class FilterConfiguration {

     @Autowired
     lateinit var userAuthenticationService: UserAuthenticationService

     @Bean
     fun authenticationFilter(): FilterRegistrationBean<Filter> {
          val registrationBean = FilterRegistrationBean<Filter>()
          registrationBean.filter = AuthenticationFilter(userAuthenticationService)
          registrationBean.addUrlPatterns("/*")
          return registrationBean
     }
}
