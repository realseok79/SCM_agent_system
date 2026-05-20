package com.sigma.scm.service;

import com.sigma.scm.domain.Region;
import com.sigma.scm.repository.RegionRepository;
import com.sigma.scm.util.RegionStandardizer;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class RegionService {

    private final RegionRepository regionRepository;
    private final RegionStandardizer regionStandardizer;

    public List<Region> getAllRegions() {
        return regionRepository.findAll();
    }

    public Optional<Region> getRegionById(Long id) {
        return regionRepository.findById(id);
    }

    public Optional<Region> getRegionByCode(String code) {
        return regionRepository.findByRegionCode(code);
    }

    @Transactional
    public Region createRegion(Region region) {
        // 지역 코드 표준화 후 저장
        String standardizedCode = regionStandardizer.standardize(region.getRegionCode());
        region.setRegionCode(standardizedCode);

        if (regionRepository.findByRegionCode(standardizedCode).isPresent()) {
            throw new IllegalArgumentException("Region code already exists: " + standardizedCode);
        }

        return regionRepository.save(region);
    }

    @Transactional
    public void deleteRegion(Long id) {
        regionRepository.deleteById(id);
    }
}
