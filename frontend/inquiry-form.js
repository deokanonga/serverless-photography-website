// The part of the website's script that sends the inquiry form to AWS.
// The full site is a single static index.html hosted on S3 behind CloudFront.

var FORM_ENDPOINT = 'https://<API_ID>.execute-api.us-east-2.amazonaws.com/inquiry';

form.addEventListener('submit', function (e) {
  e.preventDefault();
  // Quick checks in the browser; the Lambda function checks again on the server.
  if (!v('f-name') || !v('f-email') || !v('f-type')) {
    say('Please add your name, email and type of inquiry.', 'err'); return;
  }
  var data = new FormData(form);
  sendBtn.disabled = true; sendBtn.textContent = 'Sending…';
  // Sent as name=...&email=... (form-urlencoded), which the Lambda reads with parse_qs.
  fetch(FORM_ENDPOINT, { method: 'POST', body: new URLSearchParams(data), headers: { 'Accept': 'application/json' } })
    .then(function (r) { return r.json().then(function (j) { return r.ok && String(j.success) !== 'false'; }); })
    .then(function (ok) {
      if (!ok) throw new Error('failed');
      form.reset();
      say('Thank you! Your inquiry is in. I\'ll reply within 24 hours.', 'ok');
    })
    .catch(function () {
      // On any failure, keep what the visitor typed and offer email instead.
      sendBtn.disabled = false; sendBtn.textContent = 'Send inquiry';
      say('Sorry, that didn\'t go through. Please email me instead at contact@deokanonga.com.', 'err');
    });
});
