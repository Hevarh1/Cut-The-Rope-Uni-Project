// Debug script to check for overflow issues in the presentation
// Run this in the browser console

function debugPresentationOverflow() {
    const slides = document.querySelectorAll('.slides section');
    const issues = [];

    // Get actual slide dimensions
    const slideWidth = 1280;
    const slideHeight = 720;

    console.log(`=== PRESENTATION DEBUG ===`);
    console.log(`Slide dimensions: ${slideWidth}x${slideHeight}`);
    console.log(`Checking ${slides.length} slides...\n`);

    slides.forEach((slide, index) => {
        const slideId = slide.id || `slide-${index + 1}`;
        const slideTitle = slide.querySelector('h1, h2, h3')?.textContent?.substring(0, 30) || '(no title)';

        // Check slide dimensions
        const rect = slide.getBoundingClientRect();
        const scrollHeight = slide.scrollHeight;
        const scrollWidth = slide.scrollWidth;

        const verticalOverflow = scrollHeight > slideHeight;
        const horizontalOverflow = scrollWidth > slideWidth;

        if (verticalOverflow || horizontalOverflow) {
            issues.push({
                slide: slideId,
                title: slideTitle,
                verticalOverflow: verticalOverflow,
                horizontalOverflow: horizontalOverflow,
                scrollHeight: scrollHeight,
                scrollWidth: scrollWidth,
                overflowAmountV: scrollHeight - slideHeight,
                overflowAmountH: scrollWidth - slideWidth
            });
        }

        // Check specific elements
        const elements = slide.querySelectorAll('.content, .box, .callout, .fun-item, .bartle-item, .takeaway-item');
        elements.forEach(el => {
            const elRect = el.getBoundingClientRect();
            const parentRect = el.parentElement?.getBoundingClientRect();

            // Check if element overlaps with siblings
            const nextEl = el.nextElementSibling;
            if (nextEl && parentRect) {
                const nextRect = nextEl.getBoundingClientRect();
                const overlapY = elRect.bottom - nextRect.top;

                if (overlapY > 0) {
                    issues.push({
                        slide: slideId,
                        type: 'element_overlap',
                        element: el.className,
                        overlapAmount: overlapY
                    });
                }
            }
        });
    });

    // Print results
    if (issues.length === 0) {
        console.log('✅ No overflow issues detected!');
    } else {
        console.log(`❌ Found ${issues.length} issues:\n`);

        issues.forEach((issue, i) => {
            if (issue.type === 'element_overlap') {
                console.log(`${i + 1}. [${issue.slide}] OVERLAP: ${issue.element} overlaps by ${issue.overlapAmount.toFixed(0)}px`);
            } else {
                console.log(`${i + 1}. [${issue.slide}] "${issue.title.substring(0, 40)}..."`);
                if (issue.verticalOverflow) {
                    console.log(`   ⬇️ VERTICAL overflow: ${issue.scrollHeight}px > ${slideHeight}px (+${issue.overflowAmountV.toFixed(0)}px)`);
                }
                if (issue.horizontalOverflow) {
                    console.log(`   ➡️ HORIZONTAL overflow: ${issue.scrollWidth}px > ${slideWidth}px (+${issue.overflowAmountH.toFixed(0)}px)`);
                }
            }
        });
    }

    // Analyze font sizes
    console.log(`\n=== FONT SIZE ANALYSIS ===`);
    const headings = document.querySelectorAll('h1, h2, h3, h4');
    const largeFonts = [];

    headings.forEach(h => {
        const fontSize = window.getComputedStyle(h).fontSize;
        const pxSize = parseInt(fontSize);
        if (pxSize > 40) {
            largeFonts.push({
                tag: h.tagName,
                text: h.textContent?.substring(0, 30),
                size: fontSize,
                slide: h.closest('section')?.id || 'unknown'
            });
        }
    });

    if (largeFonts.length > 0) {
        console.log(`Found ${largeFonts.length} headings with large font sizes (>40px):`);
        largeFonts.forEach(f => {
            console.log(`   [${f.tag}] ${f.size} - "${f.text}..." (${f.slide})`);
        });
    }

    return issues;
}

// Run the debug
debugPresentationOverflow();
