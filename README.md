# Innervation Index Tool (Web Version)

A browser-based tool for analyzing microscopy images (TIFF, JPG, PNG) to calculate the Innervation Index (pixel density within a region of interest). This tool runs entirely in the browser using HTML5 Canvas and JavaScript, requiring no installation.

## 🚀 Features

* **Zero Installation:** Runs directly in any modern web browser (Chrome, Edge, Firefox).
* **TIFF Support:** Natively supports `.tif` and `.tiff` microscopy images (via UTIF.js).
* **Auto-Normalization:** Automatically stretches the contrast of 16-bit/dark microscopy images so they are visible immediately.
* **Image Adjustments:** Real-time controls for Contrast, Brightness, and Gaussian Blur (Noise Reduction).
* **ROI Drawing:** Draw complex polygonal Regions of Interest (ROI).
* **Smart Thresholding:** Includes **Otsu's Method** (automatic) and **Manual Cut-off** thresholds.
* **Workflow Optimization:** Designed for processing batches of images quickly (Save & Next logic).
* **Data Export:** Downloads a tab-separated `.txt` file compatible with Excel/GraphPad Prism.

## 🛠️ How to Use

### 1. Launching the Tool
If hosted on GitHub Pages, simply visit your URL (e.g., `https://username.github.io/innervation-tool`).

### 2. The Workflow
1.  **Load Folder:** Click `📂 Load Files` and select all the images you want to analyze.
2.  **Adjust Image:** Use the sliders (Contrast, Brightness) to make the nerves/structures visible.
    * *Note:* Use **Noise Blur** if the image is too grainy.
3.  **Draw ROI:**
    * Click `✏️ Draw`.
    * Click points on the image to outline the area.
    * **To Finish:** Click the Right-Click of the mouse.
4.  **Calculate:** Click `Calculate Index`. The result will appear in blue.
5.  **Save:**
    * Click `💾 Save & Next` to record the data and load the next image.
    * Click `❌ Skip` to discard the current image and move to the next.
6.  **Download:** When finished with the batch, click `⬇️ Download Results .txt`.

## 📦 Installation / Hosting

You can host this tool for free using **GitHub Pages**:

1.  Create a new GitHub repository.
2.  Add a file named `index.html` and paste the source code.
3.  Go to **Settings** -> **Pages**.
4.  Under **Branch**, select `main` (or `master`) and click **Save**.
5.  GitHub will generate a link (e.g., `https://yourname.github.io/repo-name/`) where the tool will be live.

Alternatively, you can run it locally by simply double-clicking the `index.html` file on your computer.

## 🧮 Algorithms Used

* **Auto-Normalization:** Calculates the 2nd and 98th percentiles of the image histogram and stretches the intensity values to fill the 0-255 range.
* **Otsu's Method:** An automatic clustering algorithm that finds the optimal threshold value to separate the foreground (nerves) from the background.
* **Innervation Index:** `(Count of pixels above threshold / Total pixels in ROI) * 100`

## 📄 Dependencies

* **UTIF.js:** A small, fast, and advanced TIFF decoder. Loaded via CDN.

## 📝 License

This project is open-source and available for personal and research use.
