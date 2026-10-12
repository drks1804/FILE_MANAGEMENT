from app.service.email_service import send_email

send_email("dhruvarajdrks18@gmail.com","smtp testing",
           body=(
               
        "Hello,\n\n"
        "You requested to verify your email address "
        "for the File Management System.\n\n"
        "This is a test email from the application.\n\n"
        "If you did not request this, you can ignore this email."
    
           ))

print("email sent successfully")