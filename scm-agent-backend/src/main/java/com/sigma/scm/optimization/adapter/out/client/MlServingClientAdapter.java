package com.sigma.scm.optimization.adapter.out.client;

import com.sigma.scm.optimization.application.port.out.CallMlServingPort;
import com.sigma.scm.optimization.domain.model.OptimizationItem;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.Duration;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;

@Component
@RequiredArgsConstructor
@Slf4j
public class MlServingClientAdapter implements CallMlServingPort {

    private final WebClient.Builder webClientBuilder;

    @Value("${scm.ml-serving-url:http://localhost:8000}")
    private String mlServingUrl;

    @Override
    public MlForecastResult callForecast(OptimizationItem item, String regionCode, List<Double> recentSales) {
        log.info("Querying ML Serving for demand forecast. Item: {}, Region: {}", item.getProductName(), regionCode);
        
        WebClient client = webClientBuilder.baseUrl(mlServingUrl).build();

        List<Map<String, Object>> salesPayload = new ArrayList<>();
        LocalDate today = LocalDate.now();
        for (int i = 0; i < recentSales.size(); i++) {
            Map<String, Object> record = new HashMap<>();
            record.put("date", today.minusDays(recentSales.size() - i).format(DateTimeFormatter.ISO_LOCAL_DATE));
            record.put("qty", recentSales.get(i));
            salesPayload.add(record);
        }

        List<Map<String, Object>> eventsPayload = new ArrayList<>();
        Map<String, Object> event = new HashMap<>();
        event.put("date", today.plusDays(1).format(DateTimeFormatter.ISO_LOCAL_DATE));
        event.put("is_holiday", false);
        event.put("event_type", "None");
        eventsPayload.add(event);

        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("item_id", item.getProductName());
        requestBody.put("region_code", regionCode);
        requestBody.put("recent_sales", salesPayload);
        requestBody.put("future_events", eventsPayload);

        try {
            Map<String, Object> response = client.post()
                    .uri("/api/v1/ml/predict-demand-hybrid")
                    .bodyValue(requestBody)
                    .retrieve()
                    .bodyToMono(new org.springframework.core.ParameterizedTypeReference<Map<String, Object>>() {})
                    .timeout(Duration.ofSeconds(10))
                    .block();

            if (response != null) {
                double pred10 = ((Number) response.get("predicted_demand_10")).doubleValue();
                double pred50 = ((Number) response.get("predicted_demand_50")).doubleValue();
                double pred90 = ((Number) response.get("predicted_demand_90")).doubleValue();
                @SuppressWarnings("unchecked")
                Map<String, Double> shap = (Map<String, Double>) response.get("shap_values");
                String modelVersion = (String) response.get("model_version");

                return new MlForecastResultImpl(pred10, pred50, pred90, shap, modelVersion);
            }
        } catch (Exception e) {
            log.error("Failed to query ML Serving. Falling back to Rule-based / cold start values.", e);
            throw new RuntimeException("ML Serving query failed", e);
        }

        throw new RuntimeException("Empty response from ML Serving");
    }

    private static class MlForecastResultImpl implements MlForecastResult {
        private final double predicted10;
        private final double predicted50;
        private final double predicted90;
        private final Map<String, Double> shapValues;
        private final String modelVersion;

        public MlForecastResultImpl(double predicted10, double predicted50, double predicted90, Map<String, Double> shapValues, String modelVersion) {
            this.predicted10 = predicted10;
            this.predicted50 = predicted50;
            this.predicted90 = predicted90;
            this.shapValues = shapValues;
            this.modelVersion = modelVersion;
        }

        @Override public double getPredicted10() { return predicted10; }
        @Override public double getPredicted50() { return predicted50; }
        @Override public double getPredicted90() { return predicted90; }
        @Override public Map<String, Double> getShapValues() { return shapValues; }
        @Override public String getModelVersion() { return modelVersion; }
    }
}
