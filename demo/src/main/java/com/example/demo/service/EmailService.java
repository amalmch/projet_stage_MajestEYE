package com.example.demo.service;

import jakarta.mail.MessagingException;
import jakarta.mail.internet.MimeMessage;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.stereotype.Service;
import org.thymeleaf.TemplateEngine;
import org.thymeleaf.context.Context;

@Service
@RequiredArgsConstructor
public class EmailService {

    private final JavaMailSender mailSender;
    private final TemplateEngine templateEngine;

    @Value("${spring.mail.properties.from}")
    private String fromEmail;

    public void sendVerificationEmail(String to, String name, String code) {
        Context context = new Context();
        context.setVariable("name", name);
        context.setVariable("code", code);

        String process = templateEngine.process("email-verification", context);
        sendHtmlMessage(to, "Vérifiez votre adresse e-mail - Sonede AI", process);
    }

    public void sendPasswordResetEmail(String to, String name, String code) {
        Context context = new Context();
        context.setVariable("name", name);
        context.setVariable("code", code);

        String process = templateEngine.process("password-reset", context);
        sendHtmlMessage(to, "Réinitialisation de votre mot de passe - Sonede AI", process);
    }

    private void sendHtmlMessage(String to, String subject, String htmlBody) {
        try {
            MimeMessage message = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");
            helper.setFrom(fromEmail);
            helper.setTo(to);
            helper.setSubject(subject);
            helper.setText(htmlBody, true);
            mailSender.send(message);
        } catch (MessagingException e) {
            e.printStackTrace();
            throw new RuntimeException("Failed to send email");
        }
    }
}
