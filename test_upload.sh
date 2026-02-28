#!/bin/bash

# Get auth token first
echo "Getting auth token..."
TOKEN=$(curl -s "https://alphaflow-test.d-velop.cloud/identityprovider/login" \
  -H "Authorization: Bearer 5a0sUwoprpGOAkFUbwy0/AUuKDlmcpZCMaEFBDrOVW5y8nUwx5XrOkFNXK3XtQEmmiRye34lrqgcVkZF8tKtI/WiOgzDljk5J3ulxIydRkU=&_z_A0V5ayCQ4dR3hH9gNwIU_sM7iYcHR09DmJ8vgpxNBVNDi2e8p0xZFyjhl2UxSsVO_HNosHL1Ixzo3BlMbvi3jUG74NEd0" \
  | grep -o '"AuthSessionId":"[^"]*"' | cut -d'"' -f4)

echo "Token: $TOKEN"

# Upload file
echo "Uploading file..."
curl -v "https://alphaflow-test.d-velop.cloud/alphaflow-outgoinginvoice/outgoinginvoiceservice/outgoinginvoices/697210f3bdcaeca0fa3a540e/uploadfile" \
  -H "Authorization: Bearer $TOKEN" \
  -F "upload=@test_mite_report.pdf;type=application/pdf" \
  -F "upload_fullpath=test_mite_report.pdf" \
  -F "category=62456b7ffb9b51283472ed36"
