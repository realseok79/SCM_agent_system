package com.sigma.scm.optimization.adapter.out.persistence;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sigma.scm.domain.MlInferenceLog;
import com.sigma.scm.optimization.application.port.out.SaveInferenceLogPort;
import com.sigma.scm.optimization.domain.model.ReorderDecision;
import com.sigma.scm.repository.MlInferenceLogRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Primary;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;

@Component
@Primary
@RequiredArgsConstructor
public class SaveInferenceLogAdapter implements SaveInferenceLogPort {

    private final MlInferenceLogRepository repository;
    private final ObjectMapper objectMapper;

    @Override
    public void saveInferenceLog(ReorderDecision decision) {
        MlInferenceLog log = new MlInferenceLog();
        log.setProductName(decision.getProductName());
        log.setRegionCode(decision.getRegionCode());
        log.setTargetDate(LocalDate.now().plusDays(1).format(DateTimeFormatter.ISO_LOCAL_DATE));
        log.setPredictedDemand10(decision.getPredictedDemand10());
        log.setPredictedDemand50(decision.getPredictedDemand50());
        log.setPredictedDemand90(decision.getPredictedDemand90());
        log.setModelVersion(decision.getModelVersion());

        try {
            log.setShapValues(objectMapper.writeValueAsString(decision.getShapValues()));
        } catch (Exception e) {
            log.setShapValues("{}");
        }

        repository.save(log);
    }
}
