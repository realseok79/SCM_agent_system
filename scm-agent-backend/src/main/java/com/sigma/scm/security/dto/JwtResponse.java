package com.sigma.scm.security.dto;

public record JwtResponse(
    String accessToken,
    String refreshToken,
    String tokenType,
    long expiresIn
) {
    public JwtResponse(String accessToken, String refreshToken, long expiresIn) {
        this(accessToken, refreshToken, "Bearer", expiresIn);
    }
}
