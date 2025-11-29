// Detect screen size and apply appropriate background image
function updateBackgroundImage() {
    const width = window.innerWidth;
    const body = document.body;
    
    // Remove all mobile classes
    body.classList.remove('mobile', 'mobile-small');
    
    // Add appropriate class based on screen width
    if (width <= 480) {
        body.classList.add('mobile-small');
        console.log('Screen size: mobile-small (≤480px)');
    } else if (width <= 768) {
        body.classList.add('mobile');
        console.log('Screen size: mobile (≤768px)');
    } else {
        console.log('Screen size: desktop (>768px)');
    }
}

// Run on page load
document.addEventListener('DOMContentLoaded', updateBackgroundImage);

// Run on window resize
window.addEventListener('resize', updateBackgroundImage);
