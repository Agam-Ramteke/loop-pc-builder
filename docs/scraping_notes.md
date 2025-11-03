# Web Scraping Implementation Guide - MD Computers PC Parts

# Overview

This web scraping system is designed to extract PC component data from MD Computers website through a **two-stage approach**: bulk data collection followed by detailed individual product scraping. The system uses Python with BeautifulSoup, requests, and MongoDB for comprehensive e-commerce data extraction.

## Architecture Components

### Core Files Structure

- **common_[functions.py](http://functions.py)** - Shared utilities and helper functions
- **Bulk_[data.py](http://data.py)** - First stage: Category-wise product listing scraper
- **Individual_[Data.py](http://Data.py)** - Second stage: Detailed product information extractor

---

# Stage 1: Bulk Data Collection (Bulk_[data.py](http://data.py))

## Purpose

Extracts basic product information from category listing pages to create a comprehensive product index.

## Key Features

### URL Configuration

```python
URL = [
    "[https://mdcomputers.in/catalog/processor](https://mdcomputers.in/catalog/processor)",
    "[https://mdcomputers.in/catalog/graphics-card](https://mdcomputers.in/catalog/graphics-card)", 
    "[https://mdcomputers.in/catalog/ram](https://mdcomputers.in/catalog/ram)",
    "[https://mdcomputers.in/catalog/storage](https://mdcomputers.in/catalog/storage)",
    "[https://mdcomputers.in/catalog/smps](https://mdcomputers.in/catalog/smps)",
    "[https://mdcomputers.in/catalog/cabinet](https://mdcomputers.in/catalog/cabinet)",
    "[https://mdcomputers.in/catalog/cpu-cooler](https://mdcomputers.in/catalog/cpu-cooler)"
]
```

### Data Extraction Process

1. **Category Iteration**: Processes each product category sequentially
2. **Pagination Handling**: Automatically navigates through multiple pages
3. **Product Parsing**: Extracts essential information from product grid items
4. **Duplicate Prevention**: Checks for existing daily files before scraping

### Extracted Data Fields

- Product name and URL
- Image URL (with multiple fallback strategies)
- Original and discounted prices
- Timestamp and source information
- Basic product structure for detailed scraping

### Smart Image Handling

Implements multiple strategies for image URL extraction:

```python
image_url = (
    image_el.get("src") or
    image_el.get("data-src") or
    image_el.get("data-lazy-src") or
    image_el.get("data-cfsrc")  # Cloudflare Lazy Loading
)
```

### Output Management

- **Daily File System**: Creates separate JSON files for each category per day
- **Automatic Cleanup**: Prevents duplicate scraping on same day
- **Organized Storage**: Category-based file naming convention

---

# Stage 2: Individual Product Processing (Individual_[Data.py](http://Data.py))

## Purpose

Extracts comprehensive product details and stores them in MongoDB with proper data management.

## Key Features

### Interactive File Selection

- **Timeout-based Input**: Auto-selects all files after 10 seconds
- **Selective Processing**: Option to process specific categories
- **Thread-safe Input**: Compatible with various development environments

### Dynamic Collection Mapping

```python
mapping = {
    "graphics-card": "GPUs",
    "processor": "Processors", 
    "ram": "RAM",
    "motherboard": "Motherboards",
    "smps": "smps",
    "storage": "Storage",
    "cabinet": "Cabinets"
}
```

### Detailed Product Parsing

- **Product Names**: Extracted from H1 titles
- **Pricing Information**: Current, original, and discount percentages
- **Stock Status**: Real-time availability information
- **Specifications Table**: Complete technical specifications
- **Image Management**: Local image download and storage

### Smart Storage Filtering

Implements category-specific filtering:

```python
if collection_name.lower() == "storage":
    specs_text = " ".join([f"{k} {v}".lower() for k, v in specifications.items()])
    if "internal" not in specs_text:
        print(f"Skipping Non-Internal Storage: {product_data['name']}")
        continue
```

### MongoDB Integration

- **Upsert Operations**: Prevents duplicate entries while allowing updates
- **Collection Organization**: Category-based collection structure
- **Data Freshness**: Only updates records older than 2 days

---

# Common Functions Library (common_[functions.py](http://functions.py))

## Core Utilities

### URL Processing

```python
def slugify(url: str) -> str:
    return url.replace("https://", "").replace("http://", "").replace("/", "_")
```

### File Management

- **JSON Storage**: Automated daily file creation with cleanup
- **Snapshot Saving**: HTML page preservation for parsing
- **Directory Management**: Automatic folder creation and organization

### Database Operations

### Smart Upsert Function

```python
def upsert_product(data, conn_string, db_name, collection_name, unique_keys=("url",)):
    # Inserts new or updates existing records based on freshness
    # Returns: "inserted", "updated", or "skipped"
```

### Key Features:

- **Freshness Check**: Avoids unnecessary updates for recent data
- **Flexible Unique Keys**: Configurable deduplication strategy
- **Status Reporting**: Clear feedback on operation results

### Image Processing

- **Duplicate Detection**: MD5 hash-based image deduplication
- **Database Integration**: Checks existing images before downloading
- **Error Handling**: Robust fallback mechanisms

### Pagination Support

```python
def next_page(filepath):
    soup = BeautifulSoup(filepath, "html.parser")
    next_link = soup.find("link", rel="next")
    return bool(next_link)
```

---

# Technical Implementation Details

## Rate Limiting Strategy

- **Between Pages**: 0.15-second delay during bulk collection
- **Between Products**: 2-3 second random delay for individual processing
- **Between Categories**: 1-3 second random delay

## Error Handling

- **Graceful Degradation**: Continues processing despite individual failures
- **Comprehensive Logging**: Detailed error reporting and status updates
- **Resource Cleanup**: Automatic snapshot file deletion after processing

## Data Validation

- **Required Fields**: Ensures essential data presence before storage
- **Type Checking**: Validates data types and formats
- **Consistency Checks**: Maintains data integrity across operations

## Performance Optimizations

### Memory Management

- **Snapshot Cleanup**: Immediate removal after processing
- **Batch Processing**: Efficient handling of large product catalogs
- **Connection Pooling**: Optimized database connections

### Storage Efficiency

- **Incremental Updates**: Only processes changed data
- **Compressed Storage**: Efficient JSON formatting
- **Index Optimization**: Strategic database indexing for performance

---

# Usage Workflow

## Step 1: Bulk Collection

```bash
python Bulk_[data.py](http://data.py)
```

- Scans all product categories
- Creates daily JSON files in DATA_DIR
- Skips categories already processed today

## Step 2: Individual Processing

```bash
python Individual_[Data.py](http://Data.py)
```

- Lists available JSON files
- Allows selective or complete processing
- Stores detailed data in MongoDB collections

## Step 3: Data Utilization

- Access structured data from MongoDB
- Use category-specific collections
- Leverage comprehensive product specifications

---

# Best Practices Implementation

## Respectful Scraping

- **User-Agent Rotation**: Uses fake_useragent library
- **Rate Limiting**: Implements appropriate delays
- **Error Recovery**: Handles temporary failures gracefully

## Data Integrity

- **Duplicate Prevention**: Multiple levels of deduplication
- **Timestamp Tracking**: Maintains data freshness information
- **Validation Checks**: Ensures data quality before storage

## Maintainability

- **Modular Design**: Separate concerns across files
- **Configuration Management**: Centralized settings and mappings
- **Comprehensive Documentation**: Clear code comments and structure

## Scalability Considerations

- **Horizontal Scaling**: Easy addition of new product categories
- **Database Flexibility**: Configurable MongoDB collections
- **Processing Options**: Selective category processing capabilities