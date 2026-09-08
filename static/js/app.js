const form =
    document.getElementById("verificationForm");

if (form) {

    form.addEventListener(
        "submit",
        async function (event) {

            event.preventDefault();

            const loading =
                document.getElementById(
                    "loadingBox"
                );

            const result =
                document.getElementById(
                    "resultBox"
                );

            loading.classList.remove(
                "hidden"
            );

            result.innerHTML = "";

            const formData =
                new FormData(form);

            const steps = [
                "📄 Reading uploaded document...",
                "🤖 Gemini is extracting land information...",
                "🔍 Comparing with reference records...",
                "⚠️ Detecting inconsistencies...",
                "🧠 Gemini is generating explanation..."
            ];

            let index = 0;

            const interval =
                setInterval(() => {

                    const text =
                        document.getElementById(
                            "loadingText"
                        );

                    if (text) {

                        text.innerText =
                            steps[index];

                    }

                    index =
                        (index + 1) %
                        steps.length;

                }, 1200);


            try {

                const response =
                    await fetch(
                        "/verify-land",
                        {
                            method: "POST",
                            body: formData
                        }
                    );


                const data =
                    await response.json();


                clearInterval(interval);


                loading.classList.add(
                    "hidden"
                );


                if (!data.success) {

                    result.innerHTML = `
                    <div class="error-box">
                        ❌ ${data.error}
                    </div>
                    `;

                    return;
                }


                result.innerHTML = `
                <div class="success-box">

                    <h2>
                        ✅ Verification Complete
                    </h2>

                    <p>
                        Your land document has been
                        analyzed successfully.
                    </p>

                    <a
                    href="/property/${data.property_id}"
                    class="btn primary">

                        View AI Verification Report

                    </a>

                </div>
                `;


                form.reset();


            } catch (error) {

                clearInterval(interval);

                loading.classList.add(
                    "hidden"
                );

                result.innerHTML = `
                <div class="error-box">

                    ❌ Something went wrong.

                    <p>
                    ${error.message}
                    </p>

                </div>
                `;

            }

        }
    );

}