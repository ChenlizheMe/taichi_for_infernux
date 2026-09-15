# Modified by Infernux in 2026: private compiler-relative imports.
from .ast_transformer import ASTTransformer
from .ast_transformer_utils import ASTTransformerContext


def transform_tree(tree, ctx: ASTTransformerContext):
    ASTTransformer()(ctx, tree)
    return ctx.return_data
