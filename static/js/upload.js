document.getElementById("uploadForm").addEventListener("submit", async function (e) {
    e.preventDefault();

    const form = e.target;
    const fileInput = form.querySelector("input[type='file']");
    const file = fileInput.files[0];
    const status = document.getElementById("status");

    if (!file) {
        status.innerHTML = "<span class='text-danger'>Please select a file!</span>";
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
        status.innerHTML = "⏳ Uploading...";
        const response = await fetch("/upload", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            status.innerHTML = `<span class='text-success'>✅ Upload successful: ${data.filename}</span>`;
        } else {
            status.innerHTML = `<span class='text-danger'>❌ Upload failed: ${data.error || 'Unknown error'}</span>`;
        }
    } catch (error) {
        status.innerHTML = `<span class='text-danger'>❌ Upload error: ${error.message}</span>`;
    }
});
