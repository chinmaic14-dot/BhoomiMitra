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
                "🤖 BhoomiMitra AI is extracting land information...",
                "🔍 Comparing with reference records...",
                "⚠️ Detecting inconsistencies...",
                "🧠 BhoomiMitra AI is generating explanation..."
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


                /*
                 * IMPORTANT:
                 * Render may return an HTML error page
                 * instead of JSON when the backend crashes.
                 *
                 * Do not blindly call response.json().
                 */

                const contentType =
                    response.headers.get(
                        "content-type"
                    ) || "";


                if (
                    !contentType.includes(
                        "application/json"
                    )
                ) {

                    const serverText =
                        await response.text();

                    console.error(
                        "Server returned non-JSON:",
                        serverText
                    );

                    throw new Error(
                        `Server returned ${response.status} instead of JSON.`
                    );
                }


                const data =
                    await response.json();


                clearInterval(interval);


                loading.classList.add(
                    "hidden"
                );


                if (
                    !response.ok ||
                    !data.success
                ) {

                    result.innerHTML = `
                    <div class="error-box">

                        ❌ ${
                            data.error ||
                            "Verification failed."
                        }

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

                console.error(
                    "Verification error:",
                    error
                );

                result.innerHTML = `
                <div class="error-box">

                    ❌ Something went wrong.

                    <p>
                        ${
                            error.message ||
                            "Unable to verify the land document."
                        }
                    </p>

                </div>
                `;

            }

        }
    );

}