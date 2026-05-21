package com.sigma.scm.service;

import com.sigma.scm.domain.ItemMaster;
import com.sigma.scm.optimization.adapter.in.scheduler.ReorderBatchScheduler;
import com.sigma.scm.optimization.application.port.in.ReorderProcessUseCase;
import com.sigma.scm.repository.ItemMasterRepository;
import com.sigma.scm.repository.RegionInventoryRepository;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import java.util.Arrays;
import java.util.Collections;
import static org.mockito.Mockito.*;

public class ReorderBatchSchedulerTest {

    @Test
    public void testRunDailyReorderBatch() {
        ItemMasterRepository itemMasterRepository = mock(ItemMasterRepository.class);
        RegionInventoryRepository regionInventoryRepository = mock(RegionInventoryRepository.class);
        ReorderProcessUseCase reorderProcessUseCase = mock(ReorderProcessUseCase.class);
        JdbcTemplate jdbcTemplate = mock(JdbcTemplate.class);

        ItemMaster itemA = new ItemMaster();
        itemA.setProductName("ProductA");
        ItemMaster itemB = new ItemMaster();
        itemB.setProductName("ProductB");

        when(itemMasterRepository.findAll()).thenReturn(Arrays.asList(itemA, itemB));
        when(regionInventoryRepository.findDistinctRegionCodes()).thenReturn(Arrays.asList("KR-SL", "KR-BS"));
        when(jdbcTemplate.queryForObject(eq("SELECT pg_try_advisory_lock(99099)"), eq(Boolean.class))).thenReturn(true);

        ReorderBatchScheduler scheduler = new ReorderBatchScheduler(
                itemMasterRepository,
                regionInventoryRepository,
                reorderProcessUseCase,
                jdbcTemplate
        );

        scheduler.runDailyReorderBatch();

        verify(reorderProcessUseCase, times(1)).evaluateReorder("ProductA", "KR-SL");
        verify(reorderProcessUseCase, times(1)).evaluateReorder("ProductA", "KR-BS");
        verify(reorderProcessUseCase, times(1)).evaluateReorder("ProductB", "KR-SL");
        verify(reorderProcessUseCase, times(1)).evaluateReorder("ProductB", "KR-BS");
        verify(jdbcTemplate, times(1)).execute("SELECT pg_advisory_unlock(99099)");
    }

    @Test
    public void testEmptyBatch() {
        ItemMasterRepository itemMasterRepository = mock(ItemMasterRepository.class);
        RegionInventoryRepository regionInventoryRepository = mock(RegionInventoryRepository.class);
        ReorderProcessUseCase reorderProcessUseCase = mock(ReorderProcessUseCase.class);
        JdbcTemplate jdbcTemplate = mock(JdbcTemplate.class);

        when(itemMasterRepository.findAll()).thenReturn(Collections.emptyList());
        when(regionInventoryRepository.findDistinctRegionCodes()).thenReturn(Collections.emptyList());
        when(jdbcTemplate.queryForObject(eq("SELECT pg_try_advisory_lock(99099)"), eq(Boolean.class))).thenReturn(true);

        ReorderBatchScheduler scheduler = new ReorderBatchScheduler(
                itemMasterRepository,
                regionInventoryRepository,
                reorderProcessUseCase,
                jdbcTemplate
        );

        scheduler.runDailyReorderBatch();

        verifyNoInteractions(reorderProcessUseCase);
        verify(jdbcTemplate, times(1)).execute("SELECT pg_advisory_unlock(99099)");
    }

    @Test
    public void testLockAlreadyHeld() {
        ItemMasterRepository itemMasterRepository = mock(ItemMasterRepository.class);
        RegionInventoryRepository regionInventoryRepository = mock(RegionInventoryRepository.class);
        ReorderProcessUseCase reorderProcessUseCase = mock(ReorderProcessUseCase.class);
        JdbcTemplate jdbcTemplate = mock(JdbcTemplate.class);

        // Lock acquisition fails (already held by another instance)
        when(jdbcTemplate.queryForObject(eq("SELECT pg_try_advisory_lock(99099)"), eq(Boolean.class))).thenReturn(false);

        ReorderBatchScheduler scheduler = new ReorderBatchScheduler(
                itemMasterRepository,
                regionInventoryRepository,
                reorderProcessUseCase,
                jdbcTemplate
        );

        scheduler.runDailyReorderBatch();

        // Bypasses batch completely
        verifyNoInteractions(itemMasterRepository);
        verifyNoInteractions(regionInventoryRepository);
        verifyNoInteractions(reorderProcessUseCase);
        verify(jdbcTemplate, never()).execute(anyString());
    }
}
