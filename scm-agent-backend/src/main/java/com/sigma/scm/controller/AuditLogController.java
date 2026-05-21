package com.sigma.scm.controller;

import com.sigma.scm.domain.AuditLog;
import com.sigma.scm.repository.AuditLogRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;

@RestController
@RequestMapping("/api/audit-logs")
@RequiredArgsConstructor
public class AuditLogController {

    private final AuditLogRepository auditLogRepository;

    @GetMapping
    public ResponseEntity<List<AuditLog>> getAuditLogs() {
        return ResponseEntity.ok(auditLogRepository.findAllByOrderByRecordedAtDesc());
    }

    @PostMapping
    public ResponseEntity<AuditLog> createAuditLog(@RequestBody AuditLog auditLog) {
        if (auditLog.getRecordedAt() == null) {
            auditLog.setRecordedAt(LocalDateTime.now());
        }
        return ResponseEntity.ok(auditLogRepository.save(auditLog));
    }
}
