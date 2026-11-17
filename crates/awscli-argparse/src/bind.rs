//! Compile-time checked destination binding for native handler arguments.
use crate::{Action, Argument, CliType, DefaultValue, Namespace, Nargs, Value};
/// Binding shape derived from the Rust field type.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Shape {
    Flag,
    Integer,
    String,
    StringDefault,
    Strings(usize),
    /// An option's `nargs` list of strings.
    List,
    NamedValues,
    /// A `map` argument's string pairs.
    Map,
    /// A `blob` argument's bytes.
    Blob,
}
/// A converted namespace violated the table's binding guarantees.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BindError {
    pub destination: String,
    pub shape: Shape,
}
impl std::fmt::Display for BindError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "invalid bound value for {} ({:?})",
            self.destination, self.shape
        )
    }
}
impl std::error::Error for BindError {}
/// Supported field types; each supplies its const shape and checked conversion.
pub trait BindField: Sized {
    const SHAPE: Shape;
    fn bind(namespace: &Namespace, dest: &str) -> Result<Self, BindError>;
}
impl BindField for bool {
    const SHAPE: Shape = Shape::Flag;
    fn bind(ns: &Namespace, dest: &str) -> Result<Self, BindError> {
        Ok(ns.boolean(dest))
    }
}
impl BindField for Option<i64> {
    const SHAPE: Shape = Shape::Integer;
    fn bind(ns: &Namespace, dest: &str) -> Result<Self, BindError> {
        Ok(ns.integer(dest))
    }
}
impl BindField for Option<String> {
    const SHAPE: Shape = Shape::String;
    fn bind(ns: &Namespace, dest: &str) -> Result<Self, BindError> {
        Ok(ns.string(dest).map(str::to_owned))
    }
}
impl BindField for String {
    const SHAPE: Shape = Shape::StringDefault;
    fn bind(ns: &Namespace, dest: &str) -> Result<Self, BindError> {
        ns.string(dest).map(str::to_owned).ok_or_else(|| BindError {
            destination: dest.into(),
            shape: Self::SHAPE,
        })
    }
}
/// An optional value as the OS gave it, which may not be Unicode.
impl BindField for Option<std::ffi::OsString> {
    const SHAPE: Shape = Shape::String;
    fn bind(ns: &Namespace, dest: &str) -> Result<Self, BindError> {
        Ok(ns.os_string(dest).map(std::ffi::OsStr::to_os_string))
    }
}
/// A defaulted value as the OS gave it, which may not be Unicode.
impl BindField for std::ffi::OsString {
    const SHAPE: Shape = Shape::StringDefault;
    fn bind(ns: &Namespace, dest: &str) -> Result<Self, BindError> {
        ns.os_string(dest)
            .map(std::ffi::OsStr::to_os_string)
            .ok_or_else(|| BindError {
                destination: dest.into(),
                shape: Self::SHAPE,
            })
    }
}
impl<const N: usize> BindField for [String; N] {
    const SHAPE: Shape = Shape::Strings(N);
    fn bind(ns: &Namespace, dest: &str) -> Result<Self, BindError> {
        let error = || BindError {
            destination: dest.into(),
            shape: Self::SHAPE,
        };
        let Some(Value::Array(values)) = ns.value(dest) else {
            return Err(error());
        };
        let values = values
            .iter()
            .map(|v| v.as_str().map(str::to_owned))
            .collect::<Option<Vec<_>>>()
            .ok_or_else(error)?;
        values.try_into().map_err(|_| error())
    }
}
impl<const N: usize> BindField for [std::ffi::OsString; N] {
    const SHAPE: Shape = Shape::Strings(N);
    fn bind(ns: &Namespace, dest: &str) -> Result<Self, BindError> {
        let error = || BindError {
            destination: dest.into(),
            shape: Self::SHAPE,
        };
        let Some(Value::Array(values)) = ns.value(dest) else {
            return Err(error());
        };
        let values = values
            .iter()
            .map(|value| value.as_os_str().map(std::ffi::OsStr::to_os_string))
            .collect::<Option<Vec<_>>>()
            .ok_or_else(error)?;
        values.try_into().map_err(|_| error())
    }
}
/// The strings an option's `nargs` list stored, in the order it gave them.
///
/// No option leaves the table's default, which stored none. A lone value
/// that names a parameter file stores the file's text instead of a list,
/// as upstream's `URIArgumentHandler` loads `value[0]`, so the field holds
/// one string per character of that text, as a `for` loop over the `str`
/// reads it.
impl BindField for Vec<String> {
    const SHAPE: Shape = Shape::List;
    fn bind(ns: &Namespace, dest: &str) -> Result<Self, BindError> {
        let error = || BindError {
            destination: dest.into(),
            shape: Self::SHAPE,
        };
        match ns.value(dest) {
            None | Some(Value::Null) => Ok(Vec::new()),
            Some(Value::Array(values)) => values
                .iter()
                .map(|value| value.as_str().map(str::to_owned))
                .collect::<Option<_>>()
                .ok_or_else(error),
            Some(Value::String(text)) => Ok(text.chars().map(String::from).collect()),
            Some(_) => Err(error()),
        }
    }
}
/// Each option and value an `append_named` destination collected, in order.
///
/// A pair is the option's spelling, as `N` converts it, and its one value,
/// as upstream's `AppendFilter` appends `[option_string, values[0]]`. A
/// spelling `N` rejects fails the binding. No option leaves the table's
/// default, which collected nothing.
impl<N> BindField for Vec<(N, String)>
where
    N: for<'a> TryFrom<&'a str>,
{
    const SHAPE: Shape = Shape::NamedValues;
    fn bind(ns: &Namespace, dest: &str) -> Result<Self, BindError> {
        let error = || BindError {
            destination: dest.into(),
            shape: Self::SHAPE,
        };
        let values = match ns.value(dest) {
            None | Some(Value::Null) => return Ok(Vec::new()),
            Some(Value::Array(values)) => values,
            Some(_) => return Err(error()),
        };
        values
            .iter()
            .map(|pair| match pair {
                Value::Array(pair) => match pair.as_slice() {
                    [name, value] => Some((
                        N::try_from(name.as_str()?).ok()?,
                        value.as_str()?.to_owned(),
                    )),
                    _ => None,
                },
                _ => None,
            })
            .collect::<Option<_>>()
            .ok_or_else(error)
    }
}
/// A `map` argument's string pairs, in the order its value gave them.
#[derive(Debug, Clone, Default, PartialEq, Eq, Hash)]
pub struct StringMap(pub Vec<(String, String)>);
impl BindField for StringMap {
    const SHAPE: Shape = Shape::Map;
    fn bind(ns: &Namespace, dest: &str) -> Result<Self, BindError> {
        let error = || BindError {
            destination: dest.into(),
            shape: Self::SHAPE,
        };
        let pairs = match ns.value(dest) {
            None | Some(Value::Null) => return Ok(Self::default()),
            Some(Value::Object(pairs)) => pairs,
            Some(_) => return Err(error()),
        };
        pairs
            .iter()
            .map(|(key, value)| Some((key.clone(), value.as_str()?.to_owned())))
            .collect::<Option<_>>()
            .map(Self)
            .ok_or_else(error)
    }
}
/// A `blob` argument's bytes: a string's UTF-8, or a `fileb://` file's
/// contents, which the unpack loop loaded.
impl BindField for Option<Vec<u8>> {
    const SHAPE: Shape = Shape::Blob;
    fn bind(ns: &Namespace, dest: &str) -> Result<Self, BindError> {
        match ns.value(dest) {
            None | Some(Value::Null) => Ok(None),
            Some(Value::String(text)) => Ok(Some(text.as_bytes().to_vec())),
            Some(Value::Bytes(bytes)) => Ok(Some(bytes.clone())),
            Some(_) => Err(BindError {
                destination: dest.into(),
                shape: Self::SHAPE,
            }),
        }
    }
}
/// Why a field cannot bind to a table. A Rust field type the binder does
/// not support has no reason here; it fails as an unmet `BindField` trait
/// bound instead.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ShapeError {
    /// No table argument stores to the field's destination.
    MissingDest,
    /// The named table argument stores to the destination but not the
    /// field's shape: a flag for a value, or another type or nargs.
    ShapeMismatch { argument: &'static str },
}
/// Check every argument sharing a destination against the field shape.
pub const fn check(table: &[Argument], dest: &str, shape: Shape) -> Result<(), ShapeError> {
    let mut found = false;
    let mut i = 0;
    while i < table.len() {
        let arg = table[i];
        if arg.matches_dest(dest) {
            found = true;
            if !accepts_argument(arg, shape) {
                return Err(ShapeError::ShapeMismatch { argument: arg.name });
            }
        }
        i += 1;
    }
    if found {
        Ok(())
    } else {
        Err(ShapeError::MissingDest)
    }
}
/// Whether every argument sharing a destination accepts the field shape.
pub const fn accepts(table: &[Argument], dest: &str, shape: Shape) -> bool {
    check(table, dest, shape).is_ok()
}
const fn accepts_argument(arg: Argument, shape: Shape) -> bool {
    match shape {
        Shape::Flag => matches!(arg.action, Action::StoreTrue | Action::StoreFalse),
        Shape::Integer => {
            matches!(arg.action, Action::Store)
                && arg.nargs.is_none()
                && matches!(arg.cli_type, Some(CliType::Integer))
        }
        Shape::String | Shape::StringDefault => accepts_string(arg, shape),
        Shape::Strings(n) => {
            arg.positional
                && matches!(arg.action, Action::Store)
                && arg.cli_type.is_none()
                && matches!(arg.nargs,Some(Nargs::Count(count))if count as usize==n)
        }
        Shape::List => accepts_list(arg),
        Shape::NamedValues => {
            matches!(arg.action, Action::AppendNamed)
                && matches!(arg.nargs, Some(Nargs::Count(1)))
                && arg.cli_type.is_none()
        }
        Shape::Map => accepts_typed(arg, CliType::Map),
        Shape::Blob => accepts_typed(arg, CliType::Blob),
    }
}
const fn accepts_list(arg: Argument) -> bool {
    !arg.positional
        && matches!(arg.action, Action::Store)
        && arg.cli_type.is_none()
        && matches!(arg.nargs, Some(Nargs::ZeroOrMore | Nargs::OneOrMore))
}
const fn accepts_typed(arg: Argument, cli_type: CliType) -> bool {
    matches!(arg.action, Action::Store)
        && arg.nargs.is_none()
        && matches!(
            (arg.cli_type, cli_type),
            (Some(CliType::Map), CliType::Map) | (Some(CliType::Blob), CliType::Blob)
        )
}
const fn accepts_string(arg: Argument, shape: Shape) -> bool {
    matches!(arg.action, Action::Store)
        && arg.cli_type.is_none()
        && matches!(arg.nargs, None | Some(Nargs::Optional))
        && (!matches!(shape, Shape::StringDefault)
            || matches!(arg.default, DefaultValue::String(_)))
}
/// Declare native Args, field names, shape metadata, and checked binding together.
///
/// ```
/// use awscli_argparse::{native_args, tables};
/// native_args! {
///     pub struct ListArgs for tables::LS_ARGUMENTS {
///         pub paths: String,
///         pub dir_op: bool,
///         pub page_size: Option<i64>,
///     }
/// }
/// assert_eq!(ListArgs::FIELD_NAMES, ["paths", "dir_op", "page_size"]);
/// ```
///
/// Incorrect destinations fail compilation, here with `no table argument
/// stores to dest 'page_sizes' for Bad.page_sizes`:
/// ```compile_fail
/// use awscli_argparse::{native_args, tables};
/// native_args! { struct Bad for tables::LS_ARGUMENTS { page_sizes: Option<i64> } }
/// ```
/// Incorrect shapes fail compilation, here with `Bad.page_size declares a
/// flag, which a table argument storing to dest 'page_size' does not store`:
/// ```compile_fail
/// use awscli_argparse::{native_args, tables};
/// native_args! { struct Bad for tables::LS_ARGUMENTS { page_size: bool } }
/// ```
/// Unsupported Rust field types fail compilation as an unmet `BindField`
/// bound:
/// ```compile_fail
/// use awscli_argparse::{native_args, tables};
/// native_args! { struct Bad for tables::LS_ARGUMENTS { page_size: u32 } }
/// ```
#[macro_export]
macro_rules! native_args {
    (@check $table:path, $name:ident . $field:ident : $kind:ty) => {
        match $crate::bind::check(
            $table, stringify!($field), <$kind as $crate::bind::BindField>::SHAPE
        ) {
            Ok(()) => {}
            Err($crate::bind::ShapeError::MissingDest) => panic!(concat!(
                "no table argument stores to dest '", stringify!($field), "' for ",
                stringify!($name), ".", stringify!($field)
            )),
            Err($crate::bind::ShapeError::ShapeMismatch { .. }) => {
                match <$kind as $crate::bind::BindField>::SHAPE {
                    $crate::bind::Shape::Flag => {
                        $crate::native_args!(@declares $name.$field "a flag")
                    }
                    $crate::bind::Shape::Integer => {
                        $crate::native_args!(@declares $name.$field "an integer")
                    }
                    $crate::bind::Shape::String => {
                        $crate::native_args!(@declares $name.$field "a string")
                    }
                    $crate::bind::Shape::StringDefault => $crate::native_args!(
                        @declares $name.$field "a string with a table default"
                    ),
                    $crate::bind::Shape::Strings(_) => $crate::native_args!(
                        @declares $name.$field "a positional of a fixed count"
                    ),
                    $crate::bind::Shape::List => {
                        $crate::native_args!(@declares $name.$field "a list")
                    }
                    $crate::bind::Shape::NamedValues => $crate::native_args!(
                        @declares $name.$field "a list of named values"
                    ),
                    $crate::bind::Shape::Map => {
                        $crate::native_args!(@declares $name.$field "a map")
                    }
                    $crate::bind::Shape::Blob => {
                        $crate::native_args!(@declares $name.$field "a blob")
                    }
                }
            }
        }
    };
    (@declares $name:ident . $field:ident $shape:literal) => {
        panic!(concat!(
            stringify!($name), ".", stringify!($field), " declares ", $shape,
            ", which a table argument storing to dest '", stringify!($field),
            "' does not store"
        ))
    };
    (
        $(#[$meta:meta])* $visibility:vis struct $name:ident for $table:path {
            $($field_visibility:vis $field:ident : $kind:ty),* $(,)?
        }
    ) => {
        $(#[$meta])*
        #[derive(Debug, Clone, PartialEq, Eq)]
        $visibility struct $name { $($field_visibility $field:$kind),* }
        const _: () = {
            $($crate::native_args!(@check $table, $name.$field: $kind);)*
        };
        impl $name {
            pub const FIELD_NAMES: &'static [&'static str] = &[$(stringify!($field)),*];
            pub const SHAPES: &'static [(&'static str,$crate::bind::Shape)] = &[
                $((stringify!($field), <$kind as $crate::bind::BindField>::SHAPE)),*
            ];
            pub fn bind(values:&$crate::Namespace)->Result<Self,$crate::bind::BindError> {
                Ok(Self{
                    $($field: <$kind as $crate::bind::BindField>::bind(
                        values, stringify!($field)
                    )?),*
                })
            }
        }
    };
}
#[cfg(test)]
mod tests;
