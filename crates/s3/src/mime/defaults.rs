//! Strict CPython 3.14 MIME defaults (the `mimetypes` tables of the CPython
//! release `deps/pins.toml` pins), independent of host databases.

/// `_suffix_map_default`, keyed by the lowercased suffix it rewrites.
pub(super) const SUFFIX_REWRITES: &[(&[u8], &[u8])] = &[
    (b".svgz", b".svg.gz"),
    (b".tgz", b".tar.gz"),
    (b".taz", b".tar.gz"),
    (b".tz", b".tar.gz"),
    (b".tbz2", b".tar.bz2"),
    (b".txz", b".tar.xz"),
];

/// `_encodings_map_default`'s suffixes, matched case-sensitively. Upstream
/// sends only the type, so the encoding names are not kept.
pub(super) const ENCODINGS: &[&[u8]] = &[b".gz", b".Z", b".bz2", b".xz", b".br"];

const _: () = {
    let mut index = 0;
    while index < SUFFIX_REWRITES.len() {
        let replacement = SUFFIX_REWRITES[index].1;
        assert!(!replacement.is_empty() && replacement[0] == b'.');
        let last = last_suffix(replacement);
        assert!(is_encoding(last));
        assert!(!is_rewritten(last));
        index += 1;
    }
};

const fn last_suffix(name: &[u8]) -> &[u8] {
    let mut dot = name.len();
    while dot > 0 {
        dot -= 1;
        if name[dot] == b'.' {
            break;
        }
    }
    name.split_at(dot).1
}

const fn is_encoding(suffix: &[u8]) -> bool {
    let mut index = 0;
    while index < ENCODINGS.len() {
        if bytes_equal(ENCODINGS[index], suffix) {
            return true;
        }
        index += 1;
    }
    false
}

const fn is_rewritten(suffix: &[u8]) -> bool {
    let mut index = 0;
    while index < SUFFIX_REWRITES.len() {
        if bytes_equal(SUFFIX_REWRITES[index].0, suffix) {
            return true;
        }
        index += 1;
    }
    false
}

const fn bytes_equal(left: &[u8], right: &[u8]) -> bool {
    if left.len() != right.len() {
        return false;
    }
    let mut index = 0;
    while index < left.len() {
        if left[index] != right[index] {
            return false;
        }
        index += 1;
    }
    true
}

/// `_types_map_default`, the strict table, sorted by suffix for
/// `binary_search`. The lenient `_common_types_default` is never consulted:
/// `guess_type` is strict.
pub(super) const DEFAULT_TYPES: &[(&[u8], &[u8])] = &[
    (b".3g2", b"audio/3gpp2"),
    (b".3gp", b"audio/3gpp"),
    (b".3gpp", b"audio/3gpp"),
    (b".3gpp2", b"audio/3gpp2"),
    (b".7z", b"application/x-7z-compressed"),
    (b".a", b"application/octet-stream"),
    (b".aac", b"audio/aac"),
    (b".adts", b"audio/aac"),
    (b".ai", b"application/postscript"),
    (b".aif", b"audio/x-aiff"),
    (b".aifc", b"audio/x-aiff"),
    (b".aiff", b"audio/x-aiff"),
    (b".ass", b"audio/aac"),
    (b".au", b"audio/basic"),
    (b".avi", b"video/vnd.avi"),
    (b".avif", b"image/avif"),
    (b".bat", b"text/plain"),
    (b".bcpio", b"application/x-bcpio"),
    (b".bin", b"application/octet-stream"),
    (b".bmp", b"image/bmp"),
    (b".c", b"text/plain"),
    (b".cdf", b"application/x-netcdf"),
    (b".cpio", b"application/x-cpio"),
    (b".csh", b"application/x-csh"),
    (b".css", b"text/css"),
    (b".csv", b"text/csv"),
    (b".deb", b"application/x-debian-package"),
    (b".dll", b"application/octet-stream"),
    (b".doc", b"application/msword"),
    (
        b".docx",
        b"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
    (b".dot", b"application/msword"),
    (b".dvi", b"application/x-dvi"),
    (b".emf", b"image/emf"),
    (b".eml", b"message/rfc822"),
    (b".eot", b"application/vnd.ms-fontobject"),
    (b".eps", b"application/postscript"),
    (b".epub", b"application/epub+zip"),
    (b".etx", b"text/x-setext"),
    (b".exe", b"application/octet-stream"),
    (b".fits", b"image/fits"),
    (b".flac", b"audio/flac"),
    (b".g3", b"image/g3fax"),
    (b".gif", b"image/gif"),
    (b".glb", b"model/gltf-binary"),
    (b".gltf", b"model/gltf+json"),
    (b".gtar", b"application/x-gtar"),
    (b".gz", b"application/gzip"),
    (b".h", b"text/plain"),
    (b".h5", b"application/x-hdf5"),
    (b".hdf", b"application/x-hdf"),
    (b".heic", b"image/heic"),
    (b".heif", b"image/heif"),
    (b".htm", b"text/html"),
    (b".html", b"text/html"),
    (b".ico", b"image/vnd.microsoft.icon"),
    (b".ief", b"image/ief"),
    (b".jp2", b"image/jp2"),
    (b".jpe", b"image/jpeg"),
    (b".jpeg", b"image/jpeg"),
    (b".jpg", b"image/jpeg"),
    (b".jpm", b"image/jpm"),
    (b".jpx", b"image/jpx"),
    (b".js", b"text/javascript"),
    (b".json", b"application/json"),
    (b".ksh", b"text/plain"),
    (b".latex", b"application/x-latex"),
    (b".loas", b"audio/aac"),
    (b".m1v", b"video/mpeg"),
    (b".m3u", b"application/vnd.apple.mpegurl"),
    (b".m3u8", b"application/vnd.apple.mpegurl"),
    (b".m4a", b"audio/mp4"),
    (b".m4v", b"video/x-m4v"),
    (b".man", b"application/x-troff-man"),
    (b".markdown", b"text/markdown"),
    (b".md", b"text/markdown"),
    (b".me", b"application/x-troff-me"),
    (b".mht", b"message/rfc822"),
    (b".mhtml", b"message/rfc822"),
    (b".mif", b"application/x-mif"),
    (b".mjs", b"text/javascript"),
    (b".mk3d", b"video/matroska-3d"),
    (b".mka", b"audio/matroska"),
    (b".mkv", b"video/matroska"),
    (b".mov", b"video/quicktime"),
    (b".movie", b"video/x-sgi-movie"),
    (b".mp2", b"audio/mpeg"),
    (b".mp3", b"audio/mpeg"),
    (b".mp4", b"video/mp4"),
    (b".mpa", b"video/mpeg"),
    (b".mpe", b"video/mpeg"),
    (b".mpeg", b"video/mpeg"),
    (b".mpg", b"video/mpeg"),
    (b".ms", b"application/x-troff-ms"),
    (b".n3", b"text/n3"),
    (b".nc", b"application/x-netcdf"),
    (b".nq", b"application/n-quads"),
    (b".nt", b"application/n-triples"),
    (b".nws", b"message/rfc822"),
    (b".o", b"application/octet-stream"),
    (b".obj", b"application/octet-stream"),
    (b".oda", b"application/oda"),
    (b".odg", b"application/vnd.oasis.opendocument.graphics"),
    (b".odp", b"application/vnd.oasis.opendocument.presentation"),
    (b".ods", b"application/vnd.oasis.opendocument.spreadsheet"),
    (b".odt", b"application/vnd.oasis.opendocument.text"),
    (b".ogg", b"audio/ogg"),
    (b".ogv", b"video/ogg"),
    (b".ogx", b"application/ogg"),
    (b".opus", b"audio/opus"),
    (b".otf", b"font/otf"),
    (b".p12", b"application/x-pkcs12"),
    (b".p7c", b"application/pkcs7-mime"),
    (b".pbm", b"image/x-portable-bitmap"),
    (b".pdf", b"application/pdf"),
    (b".pfx", b"application/x-pkcs12"),
    (b".pgm", b"image/x-portable-graymap"),
    (b".php", b"application/x-httpd-php"),
    (b".pl", b"text/plain"),
    (b".png", b"image/png"),
    (b".pnm", b"image/x-portable-anymap"),
    (b".pot", b"application/vnd.ms-powerpoint"),
    (b".ppa", b"application/vnd.ms-powerpoint"),
    (b".ppm", b"image/x-portable-pixmap"),
    (b".pps", b"application/vnd.ms-powerpoint"),
    (b".ppt", b"application/vnd.ms-powerpoint"),
    (
        b".pptx",
        b"application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ),
    (b".ps", b"application/postscript"),
    (b".pwz", b"application/vnd.ms-powerpoint"),
    (b".py", b"text/x-python"),
    (b".pyc", b"application/x-python-code"),
    (b".pyo", b"application/x-python-code"),
    (b".qt", b"video/quicktime"),
    (b".ra", b"audio/x-pn-realaudio"),
    (b".ram", b"application/x-pn-realaudio"),
    (b".rar", b"application/vnd.rar"),
    (b".ras", b"image/x-cmu-raster"),
    (b".rdf", b"application/xml"),
    (b".rgb", b"image/x-rgb"),
    (b".roff", b"application/x-troff"),
    (b".rpm", b"application/x-rpm"),
    (b".rst", b"text/x-rst"),
    (b".rtf", b"text/rtf"),
    (b".rtx", b"text/richtext"),
    (b".sgm", b"text/x-sgml"),
    (b".sgml", b"text/x-sgml"),
    (b".sh", b"application/x-sh"),
    (b".shar", b"application/x-shar"),
    (b".snd", b"audio/basic"),
    (b".so", b"application/octet-stream"),
    (b".src", b"application/x-wais-source"),
    (b".srt", b"text/plain"),
    (b".stl", b"model/stl"),
    (b".sv4cpio", b"application/x-sv4cpio"),
    (b".sv4crc", b"application/x-sv4crc"),
    (b".svg", b"image/svg+xml"),
    (b".swf", b"application/x-shockwave-flash"),
    (b".t", b"application/x-troff"),
    (b".t38", b"image/t38"),
    (b".tar", b"application/x-tar"),
    (b".tcl", b"application/x-tcl"),
    (b".tex", b"application/x-tex"),
    (b".texi", b"application/x-texinfo"),
    (b".texinfo", b"application/x-texinfo"),
    (b".tfx", b"image/tiff-fx"),
    (b".tif", b"image/tiff"),
    (b".tiff", b"image/tiff"),
    (b".tr", b"application/x-troff"),
    (b".trig", b"application/trig"),
    (b".tsv", b"text/tab-separated-values"),
    (b".ttf", b"font/ttf"),
    (b".txt", b"text/plain"),
    (b".ustar", b"application/x-ustar"),
    (b".vcf", b"text/x-vcard"),
    (b".vtt", b"text/vtt"),
    (b".wasm", b"application/wasm"),
    (b".wav", b"audio/vnd.wave"),
    (b".weba", b"audio/webm"),
    (b".webm", b"video/webm"),
    (b".webmanifest", b"application/manifest+json"),
    (b".webp", b"image/webp"),
    (b".wiz", b"application/msword"),
    (b".wmf", b"image/wmf"),
    (b".wmv", b"video/x-ms-wmv"),
    (b".woff", b"font/woff"),
    (b".woff2", b"font/woff2"),
    (b".wsdl", b"application/xml"),
    (b".xbm", b"image/x-xbitmap"),
    (b".xlb", b"application/vnd.ms-excel"),
    (b".xls", b"application/vnd.ms-excel"),
    (
        b".xlsx",
        b"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ),
    (b".xml", b"text/xml"),
    (b".xpdl", b"application/xml"),
    (b".xpm", b"image/x-xpixmap"),
    (b".xsl", b"application/xml"),
    (b".xwd", b"image/x-xwindowdump"),
    (b".yaml", b"application/yaml"),
    (b".yml", b"application/yaml"),
    (b".zip", b"application/zip"),
];
