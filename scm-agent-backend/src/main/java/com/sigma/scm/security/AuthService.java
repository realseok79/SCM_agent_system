package com.sigma.scm.security;

import com.sigma.scm.domain.RefreshToken;
import com.sigma.scm.domain.User;
import com.sigma.scm.repository.RefreshTokenRepository;
import com.sigma.scm.repository.UserRepository;
import com.sigma.scm.security.dto.JwtResponse;
import com.sigma.scm.security.dto.LoginRequest;
import com.sigma.scm.security.dto.RefreshTokenRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.HexFormat;

@Service
@RequiredArgsConstructor
@Transactional
@Slf4j
public class AuthService {

    private final UserRepository userRepository;
    private final RefreshTokenRepository refreshTokenRepository;
    private final JwtTokenProvider jwtTokenProvider;
    private final PasswordEncoder passwordEncoder;

    public JwtResponse login(LoginRequest request) {
        User user = userRepository.findByUsername(request.username())
                .orElseThrow(() -> new IllegalArgumentException("Invalid username or password"));

        if (!passwordEncoder.matches(request.password(), user.getPassword())) {
            throw new IllegalArgumentException("Invalid username or password");
        }

        String accessToken = jwtTokenProvider.createAccessToken(user.getId());
        String rawRefreshToken = jwtTokenProvider.createRefreshToken();
        String tokenHash = sha256(rawRefreshToken);

        // 이전 미사용 리프레시 토큰 무효화
        refreshTokenRepository.revokeAllByUserId(user.getId());

        // 새 리프레시 토큰 저장 (7일 만료)
        RefreshToken refreshToken = new RefreshToken(
                user.getId(),
                tokenHash,
                Instant.now().plus(7, ChronoUnit.DAYS)
        );
        refreshTokenRepository.save(refreshToken);

        return new JwtResponse(accessToken, rawRefreshToken, 900000); // 15분 만료
    }

    public JwtResponse refresh(RefreshTokenRequest request) {
        String rawRefreshToken = request.refreshToken();
        if (!jwtTokenProvider.validateToken(rawRefreshToken)) {
            throw new IllegalArgumentException("Invalid refresh token");
        }

        String tokenHash = sha256(rawRefreshToken);
        RefreshToken storedToken = refreshTokenRepository.findByTokenHash(tokenHash)
                .orElseThrow(() -> new IllegalArgumentException("Refresh token not found"));

        // Refresh Token Rotation (탈취 감지 정책)
        if (storedToken.isRevoked()) {
            // 이미 사용된 토큰이 요청된 경우 -> 탈취로 간주 -> 해당 유저의 모든 리프레시 토큰 폐기
            refreshTokenRepository.revokeAllByUserId(storedToken.getUserId());
            log.warn("Token reuse detected! Revoked all refresh tokens for user ID: {}", storedToken.getUserId());
            throw new SecurityException("Token reuse detected. Session terminated.");
        }

        if (storedToken.getExpiresAt().isBefore(Instant.now())) {
            throw new IllegalArgumentException("Refresh token expired");
        }

        // 사용 완료 표시 (revoked=true)
        storedToken.setRevoked(true);
        refreshTokenRepository.save(storedToken);

        // 새 토큰 세트 생성
        String newAccessToken = jwtTokenProvider.createAccessToken(storedToken.getUserId());
        String newRawRefreshToken = jwtTokenProvider.createRefreshToken();
        String newHash = sha256(newRawRefreshToken);

        RefreshToken newRefreshToken = new RefreshToken(
                storedToken.getUserId(),
                newHash,
                Instant.now().plus(7, ChronoUnit.DAYS)
        );
        refreshTokenRepository.save(newRefreshToken);

        return new JwtResponse(newAccessToken, newRawRefreshToken, 900000);
    }

    private String sha256(String text) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(text.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 algorithm not available", e);
        }
    }
}
