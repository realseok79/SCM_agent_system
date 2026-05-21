package com.sigma.scm.optimization.adapter.in.scheduler;

import com.sigma.scm.domain.ItemMaster;
import com.sigma.scm.optimization.application.port.in.ReorderProcessUseCase;
import com.sigma.scm.repository.ItemMasterRepository;
import com.sigma.scm.repository.RegionInventoryRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.concurrent.ForkJoinPool;

@Slf4j
@Component
@RequiredArgsConstructor
public class ReorderBatchScheduler {

    private final ItemMasterRepository itemMasterRepository;
    private final RegionInventoryRepository regionInventoryRepository;
    private final ReorderProcessUseCase reorderProcessUseCase;
    private final org.springframework.jdbc.core.JdbcTemplate jdbcTemplate;

    // 매일 자정에 자동 실행
    @Scheduled(cron = "0 0 0 * * ?")
    public void runDailyReorderBatch() {
        log.info("🚀 Attempting to start daily SCM optimization and reorder batch...");

        // 분산 락 획득 시도 (PostgreSQL Advisory Lock, ID: 99099)
        Boolean lockAcquired = jdbcTemplate.queryForObject("SELECT pg_try_advisory_lock(99099)", Boolean.class);
        if (lockAcquired == null || !lockAcquired) {
            log.info("🔒 Scheduler lock already held by another instance. Skipping batch execution.");
            return;
        }

        log.info("🔐 Lock acquired. Starting daily batch process...");

        try {
            List<ItemMaster> items = itemMasterRepository.findAll();
            List<String> regions = regionInventoryRepository.findDistinctRegionCodes();

            if (items.isEmpty() || regions.isEmpty()) {
                log.warn("No active items or regions found for reordering.");
                return;
            }

            log.info("Processing {} items across {} regions.", items.size(), regions.size());

            // 병렬 처리를 위해 커스텀 ForkJoinPool 사용 (FastAPI 대량 호출 병목 방지)
            ForkJoinPool customThreadPool = new ForkJoinPool(4);
            try {
                customThreadPool.submit(() -> items.parallelStream().forEach(item -> {
                    for (String region : regions) {
                        try {
                            reorderProcessUseCase.evaluateReorder(item.getProductName(), region);
                        } catch (Exception e) {
                            log.error("Failed to evaluate reorder for item: {}, region: {}. Error: {}",
                                    item.getProductName(), region, e.getMessage());
                        }
                    }
                })).get();
            } catch (Exception e) {
                log.error("Error during parallel batch reorder execution: {}", e.getMessage());
            } finally {
                customThreadPool.shutdown();
            }

            log.info("🏁 Daily SCM optimization and reorder batch completed.");
        } finally {
            jdbcTemplate.execute("SELECT pg_advisory_unlock(99099)");
            log.info("🔓 Scheduler lock released.");
        }
    }
}
