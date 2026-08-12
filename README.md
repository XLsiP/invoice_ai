# Accounts Payable

Accounts Payable is a Python application that automates invoice data entry.

The application reads invoice PDFs and images, extracts important financial
information, allows the user to review the extracted data, and generates a
structured Excel report.

The goal is to reduce repetitive manual invoice entry from hours of work to
minutes while preserving human review for accuracy.

## Version 1 Goals

The first version of Invoice AI will:

- Process multiple PDF invoices
- Extract embedded PDF text
- Use OCR when embedded text is unavailable
- Extract common invoice fields
- Validate missing or suspicious information
- Export reviewed invoice data to Excel

## Processing Pipeline

1. Validate the uploaded file
2. Extract embedded PDF text
3. Use OCR when necessary
4. Parse invoice fields
5. Validate extracted values
6. Flag uncertain information for human review
7. Export the approved data to Excel

## Initial Invoice Fields

- Source file
- Vendor name
- Invoice number
- Invoice date
- Due date
- Purchase order number
- Subtotal
- Tax
- Shipping
- Total amount
- Payment terms
- Description
- Processing status

## Privacy

Real company invoices and generated financial reports must not be committed
to the Git repository. Development should use synthetic or properly redacted
documents.
