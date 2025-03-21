# pyoxidizer.bzl
def make_python_distribution():
    dist = default_python_distribution()

    # Optimizations
    policy = dist.make_python_packaging_policy()
    policy.strip_all_shared_libraries = True  # Strip unnecessary shared libraries
    policy.optimize_bytecode = True  # Optimize Python bytecode
    policy.optimize_for_size = True  # Reduce the binary size

    # Embed the Python standard library into the binary
    dist = dist.to_python_executable(
        name="dfetch",
        packaging_policy=policy,
    )

    return dist


def make_application():
    return make_python_distribution()
