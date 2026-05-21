package com.sigma.scm.controller;

import com.sigma.scm.saeie.IngestionPipelineService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

@RestController
@RequestMapping("/api/regions")
@RequiredArgsConstructor
@Slf4j
public class IngestionController {

    private final IngestionPipelineService ingestionPipelineService;

    @PostMapping("/upload/analyze")
    public ResponseEntity<Map<String, Object>> analyzeSpreadsheet(
            @RequestParam("company_id") String companyId,
            @RequestParam("file") MultipartFile file) {
        
        try {
            log.info("[ANALYZE] Received file '{}' ({} bytes) for company '{}'",
                    file.getOriginalFilename(), file.getSize(), companyId);
            Map<String, Object> result = ingestionPipelineService.analyzeSpreadsheet(companyId, file);
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            log.error("[ANALYZE] Failed for file '{}': {}", file.getOriginalFilename(), e.getMessage(), e);
            return ResponseEntity.internalServerError().body(
                Map.of("error", e.getMessage() != null ? e.getMessage() : "Unknown error",
                       "status", "FAILED")
            );
        }
    }

    @PostMapping("/upload/confirm")
    public ResponseEntity<Map<String, Object>> confirmSpreadsheet(
            @RequestParam("company_id") String companyId,
            @RequestParam("file") MultipartFile file,
            @RequestParam("user_mapping") String userMappingJson) {
        
        try {
            log.info("[CONFIRM] Received file '{}' for company '{}' with overrides",
                    file.getOriginalFilename(), companyId);
            
            // ObjectMapper could be used here to parse JSON, or we can just pass the string to the service and let it parse it
            com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
            Map<String, String> userMapping = mapper.readValue(userMappingJson, new com.fasterxml.jackson.core.type.TypeReference<Map<String, String>>(){});
            
            Map<String, Object> result = ingestionPipelineService.confirmSpreadsheet(companyId, file, "SYSTEM", userMapping);
            log.info("[CONFIRM] Ingestion complete. Result: {}", result);
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            log.error("[CONFIRM] Ingestion failed for file '{}': {}", file.getOriginalFilename(), e.getMessage(), e);
            return ResponseEntity.internalServerError().body(
                Map.of("error", e.getMessage() != null ? e.getMessage() : "Unknown error",
                       "status", "FAILED")
            );
        }
    }

    @PostMapping("/upload/confirm")
    public ResponseEntity<Map<String, Object>> confirmSpreadsheet(
            @RequestParam("batch_id") String batchId,
            @RequestBody(required = false) Map<String, String> userOverrides) {
        
        try {
            Map<String, Object> result = ingestionPipelineService.confirmSpreadsheet(batchId, userOverrides, "SYSTEM");
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            return ResponseEntity.internalServerError().build();
        }
    }
}
