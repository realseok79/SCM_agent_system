package com.sigma.scm.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.util.HashMap;
import java.util.Map;

@Service
@Slf4j
public class SlackAlertService {

    private final WebClient webClient;
    private final String webhookUrl;

    public SlackAlertService(WebClient.Builder webClientBuilder,
                             @Value("${slack.webhook-url:}") String webhookUrl) {
        this.webClient = webClientBuilder.build();
        this.webhookUrl = webhookUrl;
    }

    /**
     * Slack 웹훅으로 비동기 장애 알림을 발송합니다.
     */
    public void sendSlackAlert(String title, String message, String severity) {
        if (webhookUrl == null || webhookUrl.trim().isEmpty()) {
            log.warn("[SLACK-ALERT] [MOCK] [Severity: {}] {} - {}", severity, title, message);
            return;
        }

        log.info("[SLACK-ALERT] Sending webhook notification to Slack. Severity: {}", severity);

        Map<String, Object> payload = new HashMap<>();
        String formattedMessage = String.format("*[%s]* %s\n\n_Details:_\n```%s```", severity.toUpperCase(), title, message);
        payload.put("text", formattedMessage);

        webClient.post()
                .uri(webhookUrl)
                .bodyValue(payload)
                .retrieve()
                .bodyToMono(Void.class)
                .doOnError(e -> log.error("[SLACK-ALERT] Failed to send Slack alert: {}", e.getMessage()))
                .subscribe(); // 비동기 백그라운드 발송
    }
}
