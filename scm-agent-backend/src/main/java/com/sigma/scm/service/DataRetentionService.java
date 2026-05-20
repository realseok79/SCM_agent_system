package com.sigma.scm.service;

import com.sigma.scm.repository.BatchStatusHistoryRepository;
import com.sigma.scm.repository.ExcelParseLogRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

@Service
@RequiredArgsConstructor
@Slf4j
public class DataRetentionService {

    private final BatchStatusHistoryRepository batchStatusHistoryRepository;
    private final ExcelParseLogRepository excelParseLogRepository;

    /**
     * 새벽 2시에 자동으로 90일 경과 로그성 데이터를 삭제하는 스케줄러
     */
    @Scheduled(cron = "0 0 2 * * ?")
    @Transactional
    public void scheduledRetentionCleanup() {
        log.info("[RETENTION] Scheduled data retention cleanup started.");
        runRetentionPolicy(90);
    }

    /**
     * 지정한 보존 기간(일) 이전의 로그를 삭제합니다.
     */
    @Transactional
    public void runRetentionPolicy(int daysToKeep) {
        LocalDateTime cutoff = LocalDateTime.now().minusDays(daysToKeep);
        log.info("[RETENTION] Deleting logs older than cutoff: {} ({} days retention)", cutoff, daysToKeep);

        try {
            int deletedHistory = batchStatusHistoryRepository.deleteOlderThan(cutoff);
            int deletedParseLogs = excelParseLogRepository.deleteOlderThan(cutoff);

            log.info("[RETENTION] Cleanup completed. Deleted {} batch_status_history rows, {} excel_parse_logs rows.",
                    deletedHistory, deletedParseLogs);
        } catch (Exception e) {
            log.error("[RETENTION] Failed to execute data retention cleanup policy: {}", e.getMessage(), e);
            throw e;
        }
    }
}
