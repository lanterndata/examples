post_count=$(ls -1 *.md | wc -l)
authors_json=$(cat authors.json)

declare -a slugs

for file in *.md; do
    # Skip README.md
    if [[ "$file" == "README.md" ]]; then
        continue
    fi

    # Check for valid file names
    if (( post_count <= 99 )); then
        [[ $file =~ ^[0-9]{2}-.*\.md$ ]] || { echo "$file should follow 2-digit naming if total posts are <= 99"; exit 1; }
    elif (( post_count <= 999 )); then
        [[ $file =~ ^[0-9]{3}-.*\.md$ ]] || { echo "$file should follow 3-digit naming if total posts are <= 999"; exit 1; }
    else
        [[ $file =~ ^[0-9]{4,}-.*\.md$ ]] || { echo "$file should follow >=4-digit naming"; exit 1; }
    fi

    # Check for valid header
    header_block=$(sed -n '/^---$/,/^---$/p' "$file")
    if [[ $(echo "$header_block" | head -n 1) != "---" || $(echo "$header_block" | tail -n 1) != "---" ]]; then
        echo "Header does not start and end with --- in $file"
        exit 1
    elif ! echo "$header_block" | grep -qE "^authors: \[[a-zA-Z0-9_-]+(, [a-zA-Z0-9_-]+)*\]$"; then
        echo "Invalid or missing authors in $file"
        exit 1
    elif ! echo "$header_block" | grep -qE "^date: [0-9]{4}-[0-9]{2}-[0-9]{2}$"; then
        echo "Invalid or missing date in $file"
        exit 1
    fi

    # Check for valid author
    author_ids=$(awk -F': ' '/authors:/ {print $2}' "$file" | tr -d '[],')
    for author_id in $author_ids; do
        echo "$authors_json" | grep "\"$author_id\":" -q || { echo "Author ID $author_id from file $file is not found in authors.json!"; exit 1; }
    done

    # Collect slugs
    slug=$(echo "$file" | sed -E 's/^[0-9]+-//;s/\.md$//')
    slugs+=("$slug")
done

# Check for duplicate slugs
sorted_slugs=($(echo "${slugs[@]}" | tr ' ' '\n' | sort | uniq -d))
for slug in "${sorted_slugs[@]}"; do
    echo "Duplicate slug found: $slug"
    exit 1
done