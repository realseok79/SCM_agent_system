package com.sigma.scm;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling // BackgroundWorker 및 스케줄링 태스크 처리를 위해 활성화
public class ScmAgentApplication {

    public static void main(String[] args) {
        SpringApplication.run(ScmAgentApplication.class, args);
    }
}
