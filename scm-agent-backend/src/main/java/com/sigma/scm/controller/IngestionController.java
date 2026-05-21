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

    @PostMapping("/upload")
    public ResponseEntity<Map<String, Object>> uploadSpreadsheet(
            @RequestParam("company_id") String companyId,
            @RequestParam("file") MultipartFile file) {
        
        try {
            log.info("[UPLOAD] Received file '{}' ({} bytes) for company '{}'",
                    file.getOriginalFilename(), file.getSize(), companyId);
            Map<String, Object> result = ingestionPipelineService.ingestSpreadsheet(companyId, file, "SYSTEM");
            log.info("[UPLOAD] Ingestion complete. Result: {}", result);
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            log.error("[UPLOAD] Ingestion failed for file '{}': {}", file.getOriginalFilename(), e.getMessage(), e);
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
