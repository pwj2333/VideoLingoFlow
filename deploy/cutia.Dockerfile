FROM node:22-alpine

WORKDIR /app
COPY thirdparty/cutia/apps/web/standalone/ ./

# The checked-in standalone trace omits this Next runtime dependency.
RUN mkdir -p apps/web/node_modules/styled-jsx \
    && npm pack styled-jsx@5.1.6 --silent \
    && tar -xzf styled-jsx-5.1.6.tgz --strip-components=1 -C apps/web/node_modules/styled-jsx \
    && rm styled-jsx-5.1.6.tgz \
    && for spec in "react@19.0.0" "react-dom@19.0.0" "scheduler@0.25.0"; do \
         name="${spec%@*}"; \
         archive="$(npm pack "$spec" --silent)"; \
         mkdir -p "apps/web/node_modules/$name"; \
         tar -xzf "$archive" --strip-components=1 -C "apps/web/node_modules/$name"; \
         rm "$archive"; \
       done

ENV NODE_ENV=production
ENV PORT=4100
ENV HOSTNAME=0.0.0.0

EXPOSE 4100
CMD ["node", "apps/web/server.js"]
